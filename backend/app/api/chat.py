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
from app.schemas.chat import ChatOperation
from app.schemas.chat import ChatResponse as ChatResponseSchema

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger("ai")

_rate_limit: dict[str, tuple[int, float]] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    week_id: str | None = None


MANAGE_PLAN_TOOL = {
    "name": "manage_plan",
    "description": "Управление планом: перенос, удаление, создание задач/пометок, изменение статуса. Используй когда пользователь просит сделать что-то с задачами, пометками или планом.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": "Твой текстовый ответ пользователю (объяснение что ты предлагаешь)",
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["move", "delete", "create", "update_status"],
                            "description": "Тип операции",
                        },
                        "item_type": {
                            "type": "string",
                            "enum": ["week_task", "day_task", "mark"],
                            "description": "Тип объекта",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "ID существующего элемента (для move/delete/update_status). Не указывай для create.",
                        },
                        "item_title": {
                            "type": "string",
                            "description": "Название элемента (для отображения пользователю + для create)",
                        },
                        "target_week_position": {
                            "type": "integer",
                            "description": "display_position целевой недели (для move и create). Не указывай для delete/update_status.",
                        },
                        "new_status": {
                            "type": "string",
                            "enum": ["done", "cancelled", "todo"],
                            "description": "Новый статус (только для update_status)",
                        },
                        "day_of_week": {
                            "type": "integer",
                            "description": "День недели 0-6 (Пн-Вс). Только для create day_task. Иначе -1.",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Краткое объяснение почему эта операция (1 предложение, на русском)",
                        },
                    },
                    "required": ["action", "item_type", "item_title", "reasoning"],
                },
            },
        },
        "required": ["reply", "operations"],
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


@router.post("", response_model=ChatResponseSchema)
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

    # Загружаем содержимое ВСЕХ недель от текущей, чтобы ИИ видел весь план
    active_weeks = [w for w in weeks if w.display_position >= current_week_pos]
    active_week_ids = [w.id for w in active_weeks]
    week_pos_by_id = {str(w.id): w.display_position for w in active_weeks}

    days_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    # Загружаем все пометки, задачи недели, задачи дня для активных недель
    all_marks_data: list[dict] = []
    all_tasks_data: list[dict] = []
    all_day_tasks_data: list[dict] = []

    if active_week_ids:
        marks_stmt = select(WeekMark).where(
            WeekMark.week_id.in_(active_week_ids), WeekMark.is_deleted == False
        )
        all_marks = (await session.execute(marks_stmt)).scalars().all()
        all_marks_data = [
            {"id": str(m.id), "title": m.title, "week": week_pos_by_id.get(str(m.week_id), "?")}
            for m in all_marks
        ]

        wt_stmt = select(WeekTask).where(
            WeekTask.week_id.in_(active_week_ids), WeekTask.is_deleted == False
        )
        all_wt = (await session.execute(wt_stmt)).scalars().all()
        all_tasks_data = [
            {
                "id": str(wt.id),
                "title": wt.title,
                "status": wt.status,
                "week": week_pos_by_id.get(str(wt.week_id), "?"),
            }
            for wt in all_wt
        ]

        dt_stmt = select(DayTask).where(
            DayTask.week_id.in_(active_week_ids), DayTask.is_deleted == False
        )
        all_dt = (await session.execute(dt_stmt)).scalars().all()
        all_day_tasks_data = [
            {
                "id": str(dt.id),
                "title": dt.title,
                "day": days_labels[dt.day_of_week],
                "status": dt.status,
                "week": week_pos_by_id.get(str(dt.week_id), "?"),
            }
            for dt in all_dt
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
        for w in active_weeks
    ]

    system_prompt = f"""Ты — ИИ-помощник в приложении «Календарь 52» для стратегического планирования жизни по методологии Weekly Thinking.
Год разбит на 52 недели, 4 квартала по 13 недель (12 рабочих + 1 отдых).
Три уровня: Год (стратегия) → Неделя (тактика) → День (операции).

Сегодня: {now.strftime("%Y-%m-%d")} (неделя #{current_week_pos}).
Доступные недели (от текущей): {json.dumps(week_list[:20], ensure_ascii=False)}
Темы пользователя: {json.dumps([t.name for t in themes], ensure_ascii=False)}
{f'Все пометки (mark) в плане: {json.dumps(all_marks_data, ensure_ascii=False)}' if all_marks_data else 'Пометок в плане нет.'}
{f'Все задачи недели (week_task) в плане: {json.dumps(all_tasks_data, ensure_ascii=False)}' if all_tasks_data else 'Задач недели в плане нет.'}
{f'Все задачи дня (day_task) в плане: {json.dumps(all_day_tasks_data, ensure_ascii=False)}' if all_day_tasks_data else 'Задач дня в плане нет.'}

Помогай пользователю планировать, отвечай на вопросы, давай советы.

## Когда использовать инструмент manage_plan:

Используй manage_plan когда пользователь просит выполнить ЛЮБОЕ действие с задачами, пометками или планом. Вот 4 доступных действия:

1. **move** — перенести задачу/пометку на другую неделю.
   Обязательно: item_id, item_type, target_week_position.
   Пример: «перенеси задачу X на неделю 20»

2. **delete** — удалить задачу/пометку.
   Обязательно: item_id, item_type.
   Пример: «удали пометку Y», «убери задачу Z»

3. **create** — создать новую задачу или пометку.
   Обязательно: item_type, item_title, target_week_position.
   Для day_task ещё нужен day_of_week (0=Пн..6=Вс).
   Пример: «добавь задачу "купить молоко" на эту неделю»

4. **update_status** — изменить статус задачи (done/cancelled/todo).
   Обязательно: item_id, item_type, new_status.
   Пример: «отметь задачу X как выполненную»

Можешь предлагать НЕСКОЛЬКО операций за раз.
Если пользователь задаёт обычный вопрос — отвечай текстом без инструмента.
Пиши БЕЗ markdown: без **жирного**, без # заголовков, без списков с * или -, без ```кода```. Только обычный текст.
Отвечай на русском, кратко и по делу."""

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    client = get_anthropic_client()
    start = time.time()
    try:
        response = client.messages.create(
            model="claude-haiku-4.5",
            max_tokens=10000,
            system=system_prompt,
            tools=[MANAGE_PLAN_TOOL],
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
        raw_operations = inp.get("operations", [])

        logger.info("Chat tool reply: %s", reply[:300])
        logger.info("Chat raw operations (%d):\n%s", len(raw_operations), json.dumps(raw_operations, ensure_ascii=False, indent=2))

        week_by_pos = {w.display_position: w for w in weeks}
        operations = []
        for op in raw_operations:
            action = op.get("action", "")
            item_type = op.get("item_type", "week_task")
            item_id = op.get("item_id")
            item_title = op.get("item_title", "")
            reasoning = op.get("reasoning", "")
            new_status = op.get("new_status")
            day_of_week = int(op.get("day_of_week", -1))

            target_week_id = None
            pos = op.get("target_week_position")
            if pos is not None:
                week_obj = week_by_pos.get(pos)
                if week_obj:
                    target_week_id = week_obj.id

            # Для move/create нужен target_week_id
            if action in ("move", "create") and not target_week_id:
                continue
            # Для delete/update_status нужен item_id
            if action in ("delete", "update_status") and not item_id:
                continue

            operations.append(
                ChatOperation(
                    action=action,
                    item_type=item_type,
                    item_id=item_id,
                    item_title=item_title,
                    target_week_id=target_week_id,
                    new_status=new_status,
                    day_of_week=day_of_week,
                    reasoning=reasoning,
                )
            )
        return ChatResponseSchema(reply=reply, operations=operations if operations else None)

    logger.info("Chat text reply (no tool): %s", " ".join(text_parts)[:300])
    return ChatResponseSchema(reply=" ".join(text_parts))
