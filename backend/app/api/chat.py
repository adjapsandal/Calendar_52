import json
import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import get_anthropic_client
from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import DayTask, Theme, User, Week, WeekMark, WeekTask, Year
from app.schemas.pile import DistributionSuggestion

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger("ai")

_rate_limit: dict[str, tuple[int, float]] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    week_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[DistributionSuggestion] | None = None


REDISTRIBUTION_TOOL = {
    "name": "propose_redistribution",
    "description": "Предложи перенос задач/пометок по неделям. Используй только когда пользователь явно просит перенести.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": "Твой ответ пользователю (текст)",
            },
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_type": {
                            "type": "string",
                            "enum": ["week_task", "day_task", "mark"],
                            "description": "Тип объекта для переноса",
                        },
                        "task_id": {"type": "string", "description": "ID объекта (week_task, day_task или mark)"},
                        "task_title": {"type": "string"},
                        "target_week_position": {"type": "integer", "description": "display_position целевой недели"},
                        "reasoning": {"type": "string", "description": "Почему именно эта неделя"},
                    },
                    "required": ["item_type", "task_id", "task_title", "target_week_position", "reasoning"],
                },
            },
        },
        "required": ["reply", "suggestions"],
    },
}


def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    count, window_start = _rate_limit.get(user_id, (0, now))
    if now - window_start > 3600:
        _rate_limit[user_id] = (1, now)
        return
    if count >= 10:
        remaining = int(3600 - (now - window_start))
        raise HTTPException(429, f"Слишком много запросов. Попробуйте через {remaining // 60} мин.")
    _rate_limit[user_id] = (count + 1, window_start)


def _week_date_range(year: int, iso_week: int) -> str:
    jan4 = datetime(year, 1, 4)
    dow = jan4.isoweekday()
    monday = jan4 - timedelta(days=dow - 1) + timedelta(weeks=iso_week - 1)
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%d.%m')}–{sunday.strftime('%d.%m')}"


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    _check_rate_limit(str(user.id))

    now = datetime.now()
    year_stmt = select(Year).where(Year.user_id == user.id, Year.year_number == now.year)
    year = (await session.execute(year_stmt)).scalar_one_or_none()

    if year:
        weeks_stmt = select(Week).where(Week.year_id == year.id).order_by(Week.display_position)
        weeks = (await session.execute(weeks_stmt)).scalars().all()
    else:
        weeks = []

    jan4 = datetime(now.year, 1, 4)
    dow = jan4.isoweekday()
    current_week_pos = ((now - (jan4 - timedelta(days=dow - 1))).days // 7) + 1
    current_week_pos = min(max(current_week_pos, 1), 52)

    current_week_tasks = []
    current_week_marks = []
    current_week_day_tasks = []
    current_week_obj = next((w for w in weeks if w.display_position == current_week_pos), None)
    load_week_id = str(current_week_obj.id) if current_week_obj else body.week_id

    if load_week_id:
        wt_stmt = select(WeekTask).where(WeekTask.week_id == load_week_id, WeekTask.is_deleted == False)
        wt_list = (await session.execute(wt_stmt)).scalars().all()

        mark_ids = [wt.mark_id for wt in wt_list if wt.mark_id]
        marks_map: dict[str, str] = {}
        if mark_ids:
            m_stmt = select(WeekMark).where(WeekMark.id.in_(mark_ids))
            marks_res = (await session.execute(m_stmt)).scalars().all()
            marks_map = {str(m.id): m.title for m in marks_res}

        current_week_tasks = [
            {
                "id": str(wt.id),
                "title": wt.title,
                "status": wt.status,
                "mark": marks_map.get(str(wt.mark_id), "") if wt.mark_id else "",
            }
            for wt in wt_list
        ]

        marks_stmt = select(WeekMark).where(WeekMark.week_id == load_week_id, WeekMark.is_deleted == False)
        marks_list = (await session.execute(marks_stmt)).scalars().all()
        current_week_marks = [{"id": str(m.id), "title": m.title} for m in marks_list]

        dt_stmt = select(DayTask).where(DayTask.week_id == load_week_id, DayTask.is_deleted == False)
        dt_list = (await session.execute(dt_stmt)).scalars().all()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        current_week_day_tasks = [
            {"id": str(dt.id), "title": dt.title, "day": days[dt.day_of_week], "status": dt.status}
            for dt in dt_list
        ]

    themes_stmt = select(Theme).where(Theme.user_id == user.id, Theme.is_deleted == False)
    themes = (await session.execute(themes_stmt)).scalars().all()

    week_list = [
        {
            "display_position": w.display_position,
            "id": str(w.id),
            "date_range": _week_date_range(year.year_number, w.iso_week) if year else "",
            "cached_load": w.cached_load,
            "is_rest_week": w.is_rest_week,
        }
        for w in weeks
        if w.display_position >= current_week_pos
    ]

    system_prompt = f"""Ты — ИИ-помощник в приложении «Календарь 52» для стратегического планирования жизни по методологии Weekly Thinking.
Год разбит на 52 недели, 4 квартала по 13 недель (12 рабочих + 1 отдых).
Три уровня: Год (стратегия) → Неделя (тактика) → День (операции).

Сегодня: {now.strftime("%Y-%m-%d")} (неделя #{current_week_pos}).
Доступные недели (от текущей): {json.dumps(week_list[:20], ensure_ascii=False)}
Темы пользователя: {json.dumps([t.name for t in themes], ensure_ascii=False)}
{f'Пометки текущей недели: {json.dumps(current_week_marks, ensure_ascii=False)}' if current_week_marks else ''}
{f'Задачи недели: {json.dumps(current_week_tasks, ensure_ascii=False)}' if current_week_tasks else ''}
{f'Задачи дня: {json.dumps(current_week_day_tasks, ensure_ascii=False)}' if current_week_day_tasks else ''}

Помогай пользователю планировать, отвечай на вопросы о планировании, давай советы.
Если пользователь просит перенести/перераспределить задачи/пометки — используй инструмент propose_redistribution. В suggestions указывай item_type: "week_task" для задач недели, "day_task" для задач дня, "mark" для пометок.
Иначе отвечай просто текстом, без инструментов.
Пиши БЕЗ markdown: без **жирного**, без # заголовков, без списков с * или -, без ```кода```. Только обычный текст.
Отвечай на русском, кратко и по делу."""

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    client = get_anthropic_client()
    start = time.time()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            tools=[REDISTRIBUTION_TOOL],
            tool_choice={"type": "auto"},
            messages=messages,
        )
    except Exception as e:
        logger.error("Chat AI failed: %s (%.1fs)", str(e)[:200], time.time() - start)
        raise HTTPException(503, "ИИ временно недоступен")

    logger.info("Chat ok: user=%s %.1fs", str(user.id)[:8], time.time() - start)

    tool_block = None
    text_parts = []
    for block in response.content:
        if block.type == "tool_use":
            tool_block = block
        elif block.type == "text":
            text_parts.append(block.text)

    if tool_block:
        inp = tool_block.input
        reply = inp.get("reply", "")
        raw_suggestions = inp.get("suggestions", [])

        week_by_pos = {w.display_position: w for w in weeks}
        suggestions = []
        for rs in raw_suggestions:
            pos = rs.get("target_week_position")
            week_obj = week_by_pos.get(pos) if pos else None
            if not week_obj:
                continue
            # use task_id as pile_item_id slot (repurposed for move operations)
            task_id = rs.get("task_id", "")
            suggestions.append(
                DistributionSuggestion(
                    pile_item_id=task_id,
                    target_week_id=week_obj.id,
                    as_mark=False,
                    title=rs.get("task_title", ""),
                    theme_id=None,
                    reasoning=rs.get("reasoning", ""),
                    item_type=rs.get("item_type", "week_task"),
                )
            )
        return ChatResponse(reply=reply, suggestions=suggestions if suggestions else None)

    return ChatResponse(reply=" ".join(text_parts))
