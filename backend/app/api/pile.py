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
    DistributionDepth,
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
    "description": "Распределяет записи из Кучи по неделям плана в виде иерархии: пометки → задачи недели → задачи дня.",
    "input_schema": {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "Порядковый номер этого элемента в массиве (0-based, последовательно)",
                        },
                        "pile_item_index": {
                            "type": "integer",
                            "description": "Индекс записи из массива pile_items (0-based)",
                        },
                        "item_type": {
                            "type": "string",
                            "enum": ["mark", "week_task", "day_task"],
                            "description": "Тип создаваемого элемента",
                        },
                        "parent_index": {
                            "type": "integer",
                            "description": "-1 для корневых пометок (mark). Для week_task: index родительской пометки. Для day_task: index родительской задачи недели.",
                        },
                        "target_week_position": {
                            "type": "integer",
                            "description": "display_position недели (1-52)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Короткое название для элемента",
                        },
                        "theme_index": {
                            "type": "integer",
                            "description": "Индекс темы из массива themes (0-based) или -1 если нет подходящей",
                        },
                        "day_of_week": {
                            "type": "integer",
                            "description": "День недели 0-6 (Пн-Вс). Только для day_task. Для остальных -1.",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Почему именно эта неделя/действие (1 предложение на русском)",
                        },
                    },
                    "required": [
                        "index", "pile_item_index", "item_type", "parent_index",
                        "target_week_position", "title", "theme_index", "day_of_week", "reasoning",
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

    depth = body.depth if body else DistributionDepth.TACTICAL

    depth_instructions = {
        DistributionDepth.STRATEGIC: """## Режим: ЛЁГКИЙ (только пометки)
Создавай ТОЛЬКО элементы с item_type="mark" и parent_index=-1.
НЕ создавай week_task и day_task.
Для каждой записи создай 1-4 пометки на разных неделях — это высокоуровневые направления/темы.
Пример: «набрать 10 кг» → пометка «Программа тренировок» на нед.23, пометка «План питания» на нед.24, пометка «Контроль прогресса» на нед.25.""",

        DistributionDepth.TACTICAL: """## Режим: СРЕДНИЙ (пометки + задачи недели)
Создавай элементы двух типов: mark и week_task.

Структура:
1. Создай пометку (item_type="mark", parent_index=-1) — это тематическое направление
2. Под ней задачи недели (item_type="week_task", parent_index=index этой пометки)

ВАЖНО:
- Родительская пометка ОБЯЗАТЕЛЬНО должна идти в массиве РАНЬШЕ своих дочерних задач (меньший index).
- Задачи МОГУТ быть на ДРУГИХ неделях, чем их родительская пометка! Пометка автоматически продублируется на каждую неделю.
- Для долгосрочных целей (1+ месяц) ОБЯЗАТЕЛЬНО распределяй задачи по разным неделям на весь период.
НЕ создавай day_task.

Пример для «набрать 10 кг за 2 месяца» (текущая неделя 23):
  index=0: mark «Программа набора массы», parent_index=-1, неделя 23
  index=1: week_task «Составить план тренировок и питания», parent_index=0, неделя 23
  index=2: week_task «Начать тренировки по программе», parent_index=0, неделя 24
  index=3: week_task «Контрольное взвешивание», parent_index=0, неделя 27
  index=4: week_task «Коррекция программы», parent_index=0, неделя 29
  index=5: week_task «Итоговые результаты», parent_index=0, неделя 31""",

        DistributionDepth.DETAILED: """## Режим: ПОДРОБНЫЙ (пометки + задачи недели + задачи дня)
Создавай элементы трёх типов: mark, week_task, day_task.

Структура (3 уровня):
1. Пометка (item_type="mark", parent_index=-1) — тематическое направление
2. Под ней задачи недели (item_type="week_task", parent_index=index пометки)
3. Под каждой задачей недели 1-2 задачи дня (item_type="day_task", parent_index=index задачи недели)
   Для day_task указывай day_of_week (0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб, 6=Вс).

ВАЖНО:
- Родители ОБЯЗАТЕЛЬНО идут в массиве РАНЬШЕ детей.
- Задачи МОГУТ быть на ДРУГИХ неделях, чем пометка! Пометка автоматически продублируется.
- Для долгосрочных целей (1+ месяц) ОБЯЗАТЕЛЬНО распределяй задачи по разным неделям.
- day_task ДОЛЖЕН быть на той же неделе, что и его родительский week_task.
- Распределяй задачи дня по разным дням, не перегружай один день.

Пример:
  index=0: mark «Программа набора массы», parent_index=-1, нед.23
  index=1: week_task «Составить план», parent_index=0, нед.23
  index=2: day_task «Рассчитать калории», parent_index=1, нед.23, day_of_week=0 (Пн)
  index=3: day_task «Выбрать программу», parent_index=1, нед.23, day_of_week=2 (Ср)
  index=4: week_task «Начать тренировки», parent_index=0, нед.24
  index=5: day_task «Первая тренировка», parent_index=4, нед.24, day_of_week=0 (Пн)""",
    }

    user_prompt = f"""Ты — ИИ-планировщик в приложении «Календарь 52» для стратегического планирования года по методологии Weekly Thinking.
Твоя задача: проанализировать записи из «Кучи», понять намерение пользователя и превратить их в конкретный план действий, распределённый по неделям.

{depth_instructions[depth]}

## Классификация записей
Перед распределением определи тип каждой записи:

ТИП 1 — КОНКРЕТНОЕ ДЕЙСТВИЕ (чёткое одноразовое действие с понятным результатом).
Примеры: «записаться к стоматологу», «купить подарок маме».
→ Создай 1 пометку + 1 задачу (или только пометку в лёгком режиме).

ТИП 2 — ЦЕЛЬ / НАМЕРЕНИЕ (абстрактное желание или долгосрочная цель).
Примеры: «набрать 15 кг мышечной массы», «выучить английский до B2».
→ Декомпозируй в несколько пометок на разных неделях с задачами под каждой.
  Шаги должны быть конкретными действиями, НЕ повторением исходной записи.

ТИП 3 — ПОВТОРЯЮЩЕЕСЯ ДЕЙСТВИЕ (действие с периодичностью).
Примеры: «ходить в зал 3 раза в неделю».
→ Создай пометки на нескольких неделях с одинаковой задачей.

## Данные

Записи из Кучи (pile_items):
{json.dumps(pile_texts, ensure_ascii=False, indent=2)}

Темы пользователя (themes):
{json.dumps(theme_list, ensure_ascii=False, indent=2)}

Недели года (weeks) — date_range = диапазон (Пн–Вс), days = конкретные даты, cached_load = текущая нагрузка:
{json.dumps(week_list, ensure_ascii=False, indent=2)}

Текущая дата: {now.strftime("%Y-%m-%d")} (неделя #{current_week_position})

## Правила:
1. НЕ предлагай прошлые недели (display_position < {current_week_position}).
2. НЕ предлагай недели отдыха (is_rest_week=true).
3. Предпочитай недели с меньшей нагрузкой (cached_load). Бюджет недели — 10 задач.
4. Если запись не подходит ни под одну тему — theme_index=-1.
5. index ОБЯЗАТЕЛЬНО последовательный: 0, 1, 2, 3...
6. Задачи недели (week_task) и задачи дня (day_task) МОГУТ быть на ДРУГИХ неделях, чем их родительская пометка. Если цель растянута на несколько недель — размещай задачи на соответствующих неделях. Пометка автоматически продублируется на каждую неделю, где есть её дочерние задачи.
7. Отвечай на русском.
8. Для долгосрочных целей (месяц+) ОБЯЗАТЕЛЬНО распределяй задачи по разным неделям в указанном временном периоде.

ОБЯЗАТЕЛЬНО вызови инструмент distribute_pile с результатом."""

    client = get_anthropic_client()
    start = time.time()
    try:
        response = client.messages.create(
            model="claude-haiku-4.5",
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
    logger.info("AI raw suggestions (%d):\n%s", len(raw_suggestions), json.dumps(raw_suggestions, ensure_ascii=False, indent=2))

    # Валидация и нормализация
    raw_suggestions = _validate_suggestions(raw_suggestions, depth)

    week_by_pos = {w.display_position: w for w in weeks}

    suggestions = []
    for i, raw in enumerate(raw_suggestions):
        idx = raw.get("pile_item_index", -1)
        if idx < 0 or idx >= len(pile_items):
            continue

        pos = raw.get("target_week_position", -1)
        week_obj = week_by_pos.get(pos)
        if not week_obj:
            continue

        theme_idx = raw.get("theme_index", -1)
        theme_id = themes[theme_idx].id if 0 <= theme_idx < len(themes) else None

        item_type = raw.get("item_type", "mark")
        as_mark = item_type == "mark"

        suggestions.append(
            DistributionSuggestion(
                pile_item_id=pile_items[idx].id,
                target_week_id=week_obj.id,
                as_mark=as_mark,
                title=raw.get("title", pile_items[idx].content[:100]),
                theme_id=theme_id,
                reasoning=raw.get("reasoning", ""),
                day_of_week=int(raw.get("day_of_week", -1)),
                item_type=item_type,
                index=raw.get("index", i),
                parent_index=raw.get("parent_index", -1),
            )
        )

    return DistributeResponse(suggestions=suggestions)


def _validate_suggestions(raw: list[dict], depth: DistributionDepth) -> list[dict]:
    """Валидация и нормализация ответа ИИ."""
    allowed_types = {
        DistributionDepth.STRATEGIC: {"mark"},
        DistributionDepth.TACTICAL: {"mark", "week_task"},
        DistributionDepth.DETAILED: {"mark", "week_task", "day_task"},
    }[depth]

    seen: dict[int, dict] = {}

    for i, s in enumerate(raw):
        # Фиксим sequential index
        s["index"] = i

        item_type = s.get("item_type", "mark")

        # Даунгрейд запрещённых типов
        if item_type not in allowed_types:
            if item_type == "day_task" and "week_task" in allowed_types:
                s["item_type"] = "week_task"
                s["day_of_week"] = -1
            else:
                s["item_type"] = "mark"
                s["parent_index"] = -1
                s["day_of_week"] = -1
            item_type = s["item_type"]

        parent_idx = s.get("parent_index", -1)

        # Проверяем parent_index
        if parent_idx != -1:
            parent = seen.get(parent_idx)
            if parent is None:
                # Orphan → promote to mark
                s["parent_index"] = -1
                s["item_type"] = "mark"
            else:
                # Проверяем type-совместимость
                parent_type = parent.get("item_type", "mark")
                if item_type == "week_task" and parent_type != "mark":
                    s["parent_index"] = -1
                    s["item_type"] = "mark"
                elif item_type == "day_task" and parent_type != "week_task":
                    s["parent_index"] = -1
                    s["item_type"] = "mark"
                else:
                    # Дети могут быть на разных неделях — не наследуем target_week_position
                    pass

        # Marks всегда root
        if s["item_type"] == "mark":
            s["parent_index"] = -1

        # day_of_week только для day_task
        if s["item_type"] != "day_task":
            s["day_of_week"] = -1

        seen[i] = s

    return raw


def _find_root(suggestion: dict, index_map: dict) -> dict | None:
    """Найти корневую пометку по цепочке parent_index."""
    current = suggestion
    visited = set()
    while current.get("parent_index", -1) != -1:
        pid = current["parent_index"]
        if pid in visited:
            return None
        visited.add(pid)
        current = index_map.get(pid)
        if current is None:
            return None
    return current


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

    # Маппинг suggestion index → DB ID для привязки иерархии
    index_to_db_id: dict[int, str] = {}
    # Маппинг (mark_index, week_id) → DB ID для клонирования пометок на другие недели
    mark_clone_map: dict[tuple[int, str], str] = {}

    # Pass 1: создать все marks
    marks = [item for item in body.items if item.item_type == "mark"]
    for item in marks:
        pi = all_items.get(item.pile_item_id)
        if pi:
            pi.distributed = True

        logger.info("apply: WeekMark title=%r week=%s index=%d", item.title, item.target_week_id, item.index)
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
        await session.flush()
        index_to_db_id[item.index] = str(mark.id)
        mark_clone_map[(item.index, str(item.target_week_id))] = str(mark.id)

    # Helper: получить или создать клон пометки на нужной неделе
    async def _get_or_clone_mark(mark_index: int, target_week_id: str) -> str | None:
        """Если mark уже на этой неделе — вернуть его ID. Иначе — клонировать."""
        key = (mark_index, target_week_id)
        if key in mark_clone_map:
            return mark_clone_map[key]

        # Найти оригинальный mark
        original_mark_id = index_to_db_id.get(mark_index)
        if not original_mark_id:
            return None

        # Найти данные оригинала
        original_item = next((m for m in marks if m.index == mark_index), None)
        if not original_item:
            return None

        # Клонировать пометку на новую неделю
        logger.info("apply: Clone WeekMark title=%r to week=%s (from mark index=%d)", original_item.title, target_week_id, mark_index)
        count_result = await session.execute(
            select(func.count()).where(WeekMark.week_id == target_week_id, WeekMark.is_deleted == False)
        )
        pos = count_result.scalar() or 0
        clone = WeekMark(
            week_id=target_week_id,
            title=original_item.title,
            theme_id=original_item.theme_id,
            position=pos,
        )
        session.add(clone)
        await session.flush()
        clone_id = str(clone.id)
        mark_clone_map[key] = clone_id
        return clone_id

    # Pass 2: создать week_tasks с привязкой к mark_id
    week_tasks = [item for item in body.items if item.item_type == "week_task"]
    for item in week_tasks:
        pi = all_items.get(item.pile_item_id)
        if pi:
            pi.distributed = True

        # Получить mark_id — если task на другой неделе, клонировать пометку
        parent_mark_id = None
        if item.parent_index >= 0:
            parent_mark_id = await _get_or_clone_mark(item.parent_index, str(item.target_week_id))

        logger.info("apply: WeekTask title=%r week=%s mark_id=%s", item.title, item.target_week_id, parent_mark_id)

        count_result = await session.execute(
            select(func.count()).where(WeekTask.week_id == item.target_week_id, WeekTask.is_deleted == False)
        )
        pos = count_result.scalar() or 0
        task = WeekTask(
            week_id=item.target_week_id,
            title=item.title,
            theme_id=item.theme_id,
            mark_id=parent_mark_id,
            position=pos,
        )
        session.add(task)
        await session.flush()
        index_to_db_id[item.index] = str(task.id)

        # Обновить cached_load
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
            week_obj.cached_load = load

    # Pass 3: создать day_tasks с привязкой к week_task_id
    day_tasks = [item for item in body.items if item.item_type == "day_task"]
    for item in day_tasks:
        pi = all_items.get(item.pile_item_id)
        if pi:
            pi.distributed = True

        parent_task_id = index_to_db_id.get(item.parent_index)
        logger.info("apply: DayTask title=%r day=%d week=%s week_task_id=%s", item.title, item.day_of_week, item.target_week_id, parent_task_id)

        day_task = DayTask(
            week_id=item.target_week_id,
            day_of_week=item.day_of_week,
            title=item.title,
            week_task_id=parent_task_id,
        )
        session.add(day_task)

    # Fallback: элементы без item_type (обратная совместимость)
    others = [item for item in body.items if item.item_type not in ("mark", "week_task", "day_task")]
    for item in others:
        pi = all_items.get(item.pile_item_id)
        if pi:
            pi.distributed = True
        if item.as_mark:
            mark = WeekMark(week_id=item.target_week_id, title=item.title, theme_id=item.theme_id, position=0)
            session.add(mark)
        else:
            task = WeekTask(week_id=item.target_week_id, title=item.title, theme_id=item.theme_id, position=0)
            session.add(task)

    applied = len(marks) + len(week_tasks) + len(day_tasks) + len(others)
    await session.commit()
    return {"ok": True, "applied": applied}
