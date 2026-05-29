import json
import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import get_anthropic_client
from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import Pile, PileItem, Theme, User, Week, WeekMark, WeekTask, DayTask, Year
from app.schemas.pile import (
    ApplyRequest,
    DistributeRequest,
    DistributeResponse,
    DistributionSuggestion,
    PileItemCreate,
    PileItemRead,
    PileItemUpdate,
)

router = APIRouter(prefix="/api/v1/pile", tags=["pile"])

logger = logging.getLogger("ai")

_rate_limit: dict[str, tuple[int, float]] = {}

DISTRIBUTION_TOOL = {
    "name": "distribute_pile",
    "description": "Распределяет записи из Кучи по неделям плана.",
    "input_schema": {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pile_item_index": {
                            "type": "integer",
                            "description": "Индекс записи из массива pile_items (0-based)",
                        },
                        "target_week_position": {
                            "type": "integer",
                            "description": "display_position первой недели (1-52)",
                        },
                        "as_mark": {
                            "type": "boolean",
                            "description": "True — создать пометку (широкая тема/направление, несколько задач). False — конкретное действие (задача).",
                        },
                        "day_of_week": {
                            "type": "integer",
                            "description": "Если запись содержит конкретный день недели — индекс (0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб, 6=Вс). -1 если конкретного дня нет. Используй только когда as_mark=false.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Короткое название для пометки/задачи",
                        },
                        "theme_index": {
                            "type": "integer",
                            "description": "Индекс темы из массива themes (0-based) или -1 если нет подходящей",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Почему именно эта неделя (1 предложение на русском)",
                        },
                        "repeat_every_weeks": {
                            "type": "integer",
                            "description": "Если запись повторяется с периодичностью — интервал в неделях (например 3). 0 означает разовое событие.",
                        },
                    },
                    "required": [
                        "pile_item_index", "target_week_position", "as_mark",
                        "title", "theme_index", "reasoning", "repeat_every_weeks", "day_of_week",
                    ],
                },
            }
        },
        "required": ["suggestions"],
    },
}


async def _get_pile(session: AsyncSession, user_id) -> Pile:
    stmt = select(Pile).where(Pile.user_id == user_id)
    return (await session.execute(stmt)).scalar_one()


_DAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _week_date_range(year: int, iso_week: int) -> str:
    jan4 = datetime(year, 1, 4)
    dow = jan4.isoweekday()
    monday = jan4 - timedelta(days=dow - 1) + timedelta(weeks=iso_week - 1)
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%d.%m')}({_DAY_LABELS[0]})–{sunday.strftime('%d.%m')}({_DAY_LABELS[6]})"


def _week_days(year: int, iso_week: int) -> dict:
    jan4 = datetime(year, 1, 4)
    dow = jan4.isoweekday()
    monday = jan4 - timedelta(days=dow - 1) + timedelta(weeks=iso_week - 1)
    return {i: (monday + timedelta(days=i)).strftime("%d.%m") for i in range(7)}


@router.get("/items", response_model=list[PileItemRead])
async def list_items(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    pile = await _get_pile(session, user.id)
    stmt = (
        select(PileItem)
        .where(PileItem.pile_id == pile.id, PileItem.distributed == False)
        .order_by(PileItem.created_at.desc())
    )
    return (await session.execute(stmt)).scalars().all()


@router.post("/items", response_model=PileItemRead)
async def create_item(
    body: PileItemCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    pile = await _get_pile(session, user.id)
    item = PileItem(pile_id=pile.id, content=body.content)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    item = await session.get(PileItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()
    return {"ok": True}


@router.patch("/items/{item_id}", response_model=PileItemRead)
async def update_item(
    item_id: str,
    body: PileItemUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    item = await session.get(PileItem, item_id)
    if not item:
        raise HTTPException(404, "Запись не найдена")
    item.content = body.content
    await session.commit()
    await session.refresh(item)
    return item


def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    count, window_start = _rate_limit.get(user_id, (0, now))
    if now - window_start > 3600:
        _rate_limit[user_id] = (1, now)
        return
    if count >= 5:
        remaining = int(3600 - (now - window_start))
        raise HTTPException(
            429,
            f"Слишком много запросов. Попробуйте через {remaining // 60} мин.",
        )
    _rate_limit[user_id] = (count + 1, window_start)


@router.post("/distribute", response_model=DistributeResponse)
async def distribute(
    body: DistributeRequest | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    _check_rate_limit(str(user.id))

    pile = await _get_pile(session, user.id)

    pile_items_stmt = select(PileItem).where(
        PileItem.pile_id == pile.id, PileItem.distributed == False
    ).order_by(PileItem.created_at.asc()).limit(50)
    pile_items = (await session.execute(pile_items_stmt)).scalars().all()

    if body and body.pile_item_ids:
        id_set = set(body.pile_item_ids)
        pile_items = [pi for pi in pile_items if pi.id in id_set]

    if not pile_items:
        raise HTTPException(400, "Нет записей для распределения")

    themes_stmt = select(Theme).where(Theme.user_id == user.id, Theme.is_deleted == False)
    themes = (await session.execute(themes_stmt)).scalars().all()

    year_stmt = select(Year).where(Year.user_id == user.id, Year.year_number == datetime.now().year)
    year = (await session.execute(year_stmt)).scalar_one_or_none()
    if not year:
        raise HTTPException(400, "Год не найден")

    weeks_stmt = select(Week).where(Week.year_id == year.id).order_by(Week.display_position)
    weeks = (await session.execute(weeks_stmt)).scalars().all()

    pile_texts = [pi.content for pi in pile_items]
    theme_list = [{"index": i, "id": str(t.id), "name": t.name} for i, t in enumerate(themes)]
    week_list = [
        {
            "display_position": w.display_position,
            "id": str(w.id),
            "date_range": _week_date_range(year.year_number, w.iso_week),
            "days": _week_days(year.year_number, w.iso_week),
            "cached_load": w.cached_load,
            "is_rest_week": w.is_rest_week,
        }
        for w in weeks
    ]

    now = datetime.now()
    jan4 = datetime(now.year, 1, 4)
    dow = jan4.isoweekday()
    current_week_position = ((now - (jan4 - timedelta(days=dow - 1))).days // 7) + 1
    current_week_position = min(max(current_week_position, 1), 52)

    user_prompt = f"""Ты — ИИ-помощник для планирования года. Распредели записи из «Кучи» по неделям.

## Записи из Кучи (pile_items):
{json.dumps(pile_texts, ensure_ascii=False, indent=2)}

## Темы пользователя (themes):
{json.dumps(theme_list, ensure_ascii=False, indent=2)}

## Недели года (weeks) — поле date_range показывает диапазон (Пн–Вс), поле days — конкретные даты каждого дня (0=Пн..6=Вс):
{json.dumps(week_list, ensure_ascii=False, indent=2)}

## Текущая дата: {now.strftime("%Y-%m-%d")} (неделя #{current_week_position})

## Правила:
1. НЕ предлагай прошлые недели (display_position < {current_week_position}).
2. НЕ предлагай выходные недели (is_rest_week=true).
3. Предпочитай недели с меньшей нагрузкой (cached_load).
4. Бюджет недели — 10 задач. Не перегружай.
5. as_mark=true если это широкая тема/направление (несколько задач). as_mark=false — конкретное действие.
6. Если as_mark=false и в записи указана конкретная дата или день недели — установи day_of_week (0=Пн..6=Вс) и выбери неделю так, чтобы поле days[day_of_week] точно совпало с упомянутой датой. Иначе day_of_week=-1.
7. Если запись не подходит ни под одну тему — theme_index = -1.
8. Каждой записи из Кучи — ровно одно предложение.
8. Используй date_range для сопоставления дат из записей с нужной неделей.
9. Если запись содержит повторяющееся действие (например «раз в 3 недели», «каждые 2 недели»), установи repeat_every_weeks в нужное значение. Тогда задача будет автоматически поставлена на несколько недель вперёд с таким интервалом.
10. Отвечай на русском."""

    client = get_anthropic_client()
    start = time.time()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            tools=[DISTRIBUTION_TOOL],
            messages=[{"role": "user", "content": user_prompt}],
            tool_choice={"type": "tool", "name": "distribute_pile"},
        )
    except Exception as e:
        logger.error("AI request failed: %s (%.1fs)", str(e)[:200], time.time() - start)
        raise HTTPException(503, "ИИ временно недоступен, попробуйте позже")

    logger.info("AI distribute ok: user=%s prompt=%dchars %.1fs", str(user.id)[:8], len(user_prompt), time.time() - start)

    tool_block = None
    for block in response.content:
        if block.type == "tool_use":
            tool_block = block
            break

    if not tool_block:
        raise HTTPException(503, "ИИ вернул неожиданный ответ")

    raw_suggestions = tool_block.input.get("suggestions", [])

    week_by_pos = {w.display_position: w for w in weeks}

    suggestions = []
    for raw in raw_suggestions:
        idx = raw.get("pile_item_index", -1)
        if idx < 0 or idx >= len(pile_items):
            continue

        pos = raw.get("target_week_position", -1)
        week_obj = week_by_pos.get(pos)
        if not week_obj:
            continue

        theme_idx = raw.get("theme_index", -1)
        theme_id = themes[theme_idx].id if 0 <= theme_idx < len(themes) else None

        repeat = max(0, int(raw.get("repeat_every_weeks", 0)))
        positions_to_add = [pos]
        if repeat > 0:
            next_pos = pos + repeat
            while next_pos <= 52:
                candidate = week_by_pos.get(next_pos)
                if candidate and not candidate.is_rest_week:
                    positions_to_add.append(next_pos)
                next_pos += repeat

        for week_pos in positions_to_add:
            week_for_pos = week_by_pos.get(week_pos)
            if not week_for_pos:
                continue
            reasoning = raw.get("reasoning", "")
            if len(positions_to_add) > 1:
                reasoning = f"Повтор каждые {repeat} нед. · " + reasoning
            suggestions.append(
                DistributionSuggestion(
                    pile_item_id=pile_items[idx].id,
                    target_week_id=week_for_pos.id,
                    as_mark=raw.get("as_mark", False),
                    title=raw.get("title", pile_items[idx].content[:100]),
                    theme_id=theme_id,
                    reasoning=reasoning,
                    day_of_week=int(raw.get("day_of_week", -1)),
                )
            )

    return DistributeResponse(suggestions=suggestions)


@router.post("/distribute/apply")
async def apply_distribution(
    body: ApplyRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    pile = await _get_pile(session, user.id)

    pile_items_stmt = select(PileItem).where(
        PileItem.pile_id == pile.id, PileItem.distributed == False
    )
    all_items = {pi.id: pi for pi in (await session.execute(pile_items_stmt)).scalars().all()}

    from app.models import TaskStatus

    applied = 0
    for item in body.items:
        pi = all_items.get(item.pile_item_id)
        if not pi:
            logger.warning("apply: pile_item_id %s not found or already distributed", item.pile_item_id)
            continue

        pi.distributed = True

        if item.as_mark:
            logger.info("apply: WeekMark title=%r week=%s", item.title, item.target_week_id)
            count_result = await session.execute(
                select(func.count()).where(WeekMark.week_id == item.target_week_id, WeekMark.is_deleted == False)
            )
            pos = count_result.scalar() or 0
            mark = WeekMark(
                week_id=item.target_week_id,
                title=item.title,
                theme_id=item.theme_id,
                position=pos,
            )
            session.add(mark)
        elif item.day_of_week >= 0:
            logger.info("apply: DayTask title=%r day=%d week=%s", item.title, item.day_of_week, item.target_week_id)
            day_task = DayTask(
                week_id=item.target_week_id,
                day_of_week=item.day_of_week,
                title=item.title,
            )
            session.add(day_task)
        else:
            logger.info("apply: WeekTask title=%r week=%s", item.title, item.target_week_id)
            count_result = await session.execute(
                select(func.count()).where(WeekTask.week_id == item.target_week_id, WeekTask.is_deleted == False)
            )
            pos = count_result.scalar() or 0
            task = WeekTask(
                week_id=item.target_week_id,
                title=item.title,
                theme_id=item.theme_id,
                position=pos,
            )
            session.add(task)

            load_result = await session.execute(
                select(func.count()).where(
                    WeekTask.week_id == item.target_week_id,
                    WeekTask.is_deleted == False,
                    WeekTask.status == TaskStatus.todo.value,
                )
            )
            load = load_result.scalar() or 0
            week_obj = await session.get(Week, item.target_week_id)
            if week_obj:
                week_obj.cached_load = load + 1

        applied += 1

    await session.commit()
    return {"ok": True, "applied": applied}
