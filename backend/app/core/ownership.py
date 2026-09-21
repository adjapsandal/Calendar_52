"""Загрузка объектов с проверкой владения.

Все сущности плана принадлежат пользователю по цепочке
``DayTask/WeekTask/WeekMark -> Week -> Year -> User``, темы и настройки —
напрямую через ``user_id``. Роутеры обязаны получать объекты только через
функции этого модуля: прямой ``session.get(Model, id)`` не проверяет
владельца и позволяет читать и изменять чужие данные по UUID.

При отсутствии объекта и при попытке обратиться к чужому возвращается
одинаковый 404 — чтобы по коду ответа нельзя было определить, существует
ли объект у другого пользователя.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DayTask, Theme, User, Week, WeekMark, WeekTask, Year

NOT_FOUND = "Объект не найден"


def to_uuid(value: str | UUID) -> UUID:
    """Привести идентификатор из пути к UUID, не роняя запрос в 500."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(404, NOT_FOUND) from None


async def get_owned_week(session: AsyncSession, week_id: str | UUID, user: User) -> Week:
    stmt = (
        select(Week)
        .join(Year, Week.year_id == Year.id)
        .where(Week.id == to_uuid(week_id), Year.user_id == user.id)
    )
    week = (await session.execute(stmt)).scalar_one_or_none()
    if week is None:
        raise HTTPException(404, NOT_FOUND)
    return week


async def get_owned_mark(session: AsyncSession, mark_id: str | UUID, user: User) -> WeekMark:
    stmt = (
        select(WeekMark)
        .join(Week, WeekMark.week_id == Week.id)
        .join(Year, Week.year_id == Year.id)
        .where(
            WeekMark.id == to_uuid(mark_id),
            WeekMark.is_deleted == False,  # noqa: E712 — SQL-выражение, не Python-bool
            Year.user_id == user.id,
        )
    )
    mark = (await session.execute(stmt)).scalar_one_or_none()
    if mark is None:
        raise HTTPException(404, NOT_FOUND)
    return mark


async def get_owned_week_task(session: AsyncSession, task_id: str | UUID, user: User) -> WeekTask:
    stmt = (
        select(WeekTask)
        .join(Week, WeekTask.week_id == Week.id)
        .join(Year, Week.year_id == Year.id)
        .where(
            WeekTask.id == to_uuid(task_id),
            WeekTask.is_deleted == False,  # noqa: E712
            Year.user_id == user.id,
        )
    )
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise HTTPException(404, NOT_FOUND)
    return task


async def get_owned_day_task(session: AsyncSession, task_id: str | UUID, user: User) -> DayTask:
    stmt = (
        select(DayTask)
        .join(Week, DayTask.week_id == Week.id)
        .join(Year, Week.year_id == Year.id)
        .where(
            DayTask.id == to_uuid(task_id),
            DayTask.is_deleted == False,  # noqa: E712
            Year.user_id == user.id,
        )
    )
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise HTTPException(404, NOT_FOUND)
    return task


async def get_owned_theme(session: AsyncSession, theme_id: str | UUID, user: User) -> Theme:
    stmt = select(Theme).where(
        Theme.id == to_uuid(theme_id),
        Theme.is_deleted == False,  # noqa: E712
        Theme.user_id == user.id,
    )
    theme = (await session.execute(stmt)).scalar_one_or_none()
    if theme is None:
        raise HTTPException(404, NOT_FOUND)
    return theme
