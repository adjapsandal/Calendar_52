from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import User, Week, WeekMark
from app.schemas.week import WeekDetail, WeekMarkRead

router = APIRouter(prefix="/api/v1", tags=["weeks"])


@router.get("/weeks/{week_id}", response_model=WeekDetail)
async def get_week(
    week_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(Week)
        .where(Week.id == week_id)
        .options(
            selectinload(Week.marks).selectinload(WeekMark.theme),
            selectinload(Week.week_tasks),
            selectinload(Week.day_tasks),
            selectinload(Week.year),
        )
    )
    week = (await session.execute(stmt)).scalar_one()

    marks = [m for m in week.marks if not m.is_deleted]
    week_tasks = [t for t in week.week_tasks if not t.is_deleted]
    day_tasks = [t for t in week.day_tasks if not t.is_deleted]

    mark_reads = [
        WeekMarkRead(
            id=m.id,
            theme_id=m.theme_id,
            theme_color=m.theme.color if m.theme else None,
            title=m.title,
            description=m.description,
            position=m.position,
        )
        for m in sorted(marks, key=lambda m: m.position)
    ]

    return WeekDetail(
        id=week.id,
        iso_week=week.iso_week,
        display_position=week.display_position,
        quarter=week.quarter,
        is_rest_week=week.is_rest_week,
        cached_load=week.cached_load,
        year_number=week.year.year_number,
        marks=mark_reads,
        week_tasks=sorted(week_tasks, key=lambda t: t.position),
        day_tasks=sorted(day_tasks, key=lambda t: (t.day_of_week, t.position)),
    )
