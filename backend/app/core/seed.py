import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Pile,
    QuarterNote,
    Settings,
    Theme,
    Week,
    Year,
)

DEFAULT_THEMES = [
    ("Работа", "#3B82F6"),
    ("Здоровье", "#22C55E"),
    ("Семья", "#F59E0B"),
    ("Обучение", "#8B5CF6"),
    ("Личное", "#EC4899"),
]


async def seed_year(session: AsyncSession, user_id, year_number: int) -> Year:
    stmt = select(Year).where(Year.user_id == user_id, Year.year_number == year_number)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    year = Year(user_id=user_id, year_number=year_number)
    session.add(year)
    await session.flush()

    for q in range(1, 5):
        session.add(QuarterNote(year_id=year.id, quarter=q, content=""))

    pos = 1
    for q in range(1, 5):
        for w in range(1, 14):
            iso_week = (q - 1) * 13 + w
            session.add(
                Week(
                    year_id=year.id,
                    iso_week=iso_week,
                    display_position=pos,
                    quarter=q,
                    is_rest_week=(w == 13),
                )
            )
            pos += 1

    await session.commit()
    return year


async def seed_user_data(session: AsyncSession, user_id) -> None:
    existing = await session.execute(
        select(Settings).where(Settings.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        return

    session.add(Settings(user_id=user_id))

    for name, color in DEFAULT_THEMES:
        session.add(Theme(user_id=user_id, name=name, color=color))

    session.add(Pile(user_id=user_id))

    year_number = datetime.datetime.now().year
    await seed_year(session, user_id, year_number)
