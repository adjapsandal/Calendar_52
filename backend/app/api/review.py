from datetime import datetime
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import get_anthropic_client
from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import User, Week, WeekMark, WeekTask, WeeklyReview
from app.schemas.review import (
    ReflectRequest,
    ReviewCompleteResponse,
    ReviewRead,
    ReviewStartResponse,
)

router = APIRouter(prefix="/api/v1", tags=["review"])

REVIEW_TOOL = {
    "name": "weekly_reflection",
    "description": "Структурирует рефлексию пользователя по итогам недели.",
    "input_schema": {
        "type": "object",
        "properties": {
            "achievements": {
                "type": "string",
                "description": "Достижения недели (2-3 предложения на русском)",
            },
            "lessons": {
                "type": "string",
                "description": "Уроки и выводы (2-3 предложения на русском)",
            },
            "corrections": {
                "type": "string",
                "description": "Корректировки на следующую неделю (2-3 предложения на русском)",
            },
            "tails": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "suggested_action": {
                            "type": "string",
                            "enum": ["carry_over", "drop"],
                        },
                    },
                    "required": ["task_id", "suggested_action"],
                },
                "description": "Незакрытые задачи с рекомендацией: carry_over — перенести, drop — удалить",
            },
        },
        "required": ["achievements", "lessons", "corrections", "tails"],
    },
}


@router.post("/weeks/{week_id}/review/start", response_model=ReviewStartResponse)
async def start_review(
    week_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Week)
        .where(Week.id == week_id)
        .options(
            selectinload(Week.marks),
            selectinload(Week.week_tasks),
        )
    )
    week = (await session.execute(stmt)).scalar_one_or_none()
    if not week:
        raise HTTPException(404, "Неделя не найдена")

    marks = [m for m in week.marks if not m.is_deleted]
    tasks = [t for t in week.week_tasks if not t.is_deleted]

    existing = await session.execute(
        select(WeeklyReview).where(WeeklyReview.week_id == week_id)
    )
    review = existing.scalar_one_or_none()

    return ReviewStartResponse(
        week_id=week.id,
        display_position=week.display_position,
        marks=[
            {"id": m.id, "title": m.title}
            for m in sorted(marks, key=lambda m: m.position)
        ],
        tasks=[
            {"id": t.id, "title": t.title, "status": t.status, "mark_id": t.mark_id}
            for t in sorted(tasks, key=lambda t: t.position)
        ],
        existing_review=ReviewRead.model_validate(review) if review else None,
    )


@router.post("/weeks/{week_id}/review/reflect")
async def reflect(
    week_id: str,
    body: ReflectRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(Week).where(Week.id == week_id)
    week = (await session.execute(stmt)).scalar_one_or_none()
    if not week:
        raise HTTPException(404, "Неделя не найдена")

    tasks_stmt = select(WeekTask).where(WeekTask.week_id == week_id, WeekTask.is_deleted == False)
    tasks = (await session.execute(tasks_stmt)).scalars().all()

    for t in body.task_statuses:
        task = await session.get(WeekTask, t.id)
        if task and task.week_id == UUID(week_id):
            task.status = t.status
    await session.commit()

    tasks_refreshed = (await session.execute(tasks_stmt)).scalars().all()

    task_summary = "\n".join(
        f"- [{t.status}] {t.title}" for t in tasks_refreshed
    )
    undone = [t for t in tasks_refreshed if t.status == "todo"]

    user_prompt = f"""Ты — ИИ-коуч для планирования. Пользователь закрывает неделю {week.display_position}.

## Задачи недели (финальные статусы):
{task_summary}

## Незакрытые задачи (статус todo):
{json_dumps([{"id": str(t.id), "title": t.title} for t in undone], ensure_ascii=False)}

## Рефлексия пользователя:
{body.raw_input or "(пользователь пропустил рефлексию)"}

## Задача:
1. Выдели достижения недели (achievements) — что получилось.
2. Выдели уроки (lessons) — что не вышло и почему.
3. Предложи корректировки (corrections) — что изменить на следующей неделе.
4. Для каждой незакрытой задачи предложи действие: carry_over (перенести) или drop (удалить).
5. Отвечай на русском."""

    import json as json_mod

    client = get_anthropic_client()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            tools=[REVIEW_TOOL],
            messages=[{"role": "user", "content": user_prompt}],
            tool_choice={"type": "tool", "name": "weekly_reflection"},
        )
    except Exception as e:
        import logging
        logging.getLogger("ai").error("Review AI failed: %s", str(e)[:200])
        raise HTTPException(503, "ИИ временно недоступен")

    tool_block = None
    for block in response.content:
        if block.type == "tool_use":
            tool_block = block
            break

    if not tool_block:
        raise HTTPException(503, "ИИ вернул неожиданный ответ")

    result = tool_block.input

    review = WeeklyReview(
        week_id=UUID(week_id),
        raw_input=body.raw_input or "",
        achievements=result.get("achievements", ""),
        lessons=result.get("lessons", ""),
        corrections=result.get("corrections", ""),
    )

    existing = await session.execute(
        select(WeeklyReview).where(WeeklyReview.week_id == week_id)
    )
    existing_review = existing.scalar_one_or_none()
    if existing_review:
        existing_review.raw_input = review.raw_input
        existing_review.achievements = review.achievements
        existing_review.lessons = review.lessons
        existing_review.corrections = review.corrections
    else:
        session.add(review)

    await session.commit()

    return {
        "achievements": review.achievements,
        "lessons": review.lessons,
        "corrections": review.corrections,
        "tails": result.get("tails", []),
    }


@router.post("/weeks/{week_id}/review/complete", response_model=ReviewCompleteResponse)
async def complete_review(
    week_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    undone = (await session.execute(
        select(WeekTask).where(
            WeekTask.week_id == week_id,
            WeekTask.is_deleted == False,
            WeekTask.status == "todo",
        )
    )).scalars().all()

    for t in undone:
        t.status = "cancelled"

    await session.commit()

    return ReviewCompleteResponse(ok=True, cancelled_count=len(undone))


def json_dumps(obj, **kwargs):
    import json
    return json.dumps(obj, **kwargs)
