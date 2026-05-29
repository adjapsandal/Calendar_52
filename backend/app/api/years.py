from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.core.seed import seed_year
from app.models import QuarterNote, Theme, User, Week, WeekMark, WeekTask, Year
from app.schemas.year import (
    QuarterBlock,
    QuarterNoteRead,
    QuarterNoteWrite,
    YearRead,
)

router = APIRouter(prefix="/api/v1", tags=["years"])


@router.get("/years/{year_number}", response_model=YearRead)
async def get_year(
    year_number: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(Year)
        .where(Year.user_id == user.id, Year.year_number == year_number)
        .options(
            selectinload(Year.weeks).selectinload(Week.marks).selectinload(WeekMark.theme),
            selectinload(Year.weeks).selectinload(Week.week_tasks),
        )
    )
    year = (await session.execute(stmt)).scalar_one_or_none()

    if year is None:
        year = await seed_year(session, user.id, year_number)
        stmt = (
            select(Year)
            .where(Year.id == year.id)
            .options(
                selectinload(Year.weeks).selectinload(Week.marks).selectinload(WeekMark.theme),
                selectinload(Year.weeks).selectinload(Week.week_tasks),
            )
        )
        year = (await session.execute(stmt)).scalar_one()

    notes_stmt = select(QuarterNote).where(QuarterNote.year_id == year.id)
    notes = (await session.execute(notes_stmt)).scalars().all()
    notes_by_q = {n.quarter: n for n in notes}

    quarters = []
    for q in range(1, 5):
        q_weeks = sorted(
            [w for w in year.weeks if w.quarter == q],
            key=lambda w: w.display_position,
        )
        note = notes_by_q.get(q)
        quarters.append(
            QuarterBlock(
                quarter=q,
                weeks=[
                    _week_brief(w) for w in q_weeks
                ],
                note=QuarterNoteRead(
                    id=note.id if note else None,
                    quarter=q,
                    content=note.content if note else "",
                ),
            )
        )

    return YearRead(id=year.id, year_number=year.year_number, quarters=quarters)


@router.get("/years/{year_number}/quarters/{q}/note", response_model=QuarterNoteRead)
async def get_quarter_note(
    year_number: int,
    q: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    year = await _get_or_create_year(session, user.id, year_number)
    note = await _get_note(session, year.id, q)
    return QuarterNoteRead(
        id=note.id if note else None,
        quarter=q,
        content=note.content if note else "",
    )


@router.put("/years/{year_number}/quarters/{q}/note", response_model=QuarterNoteRead)
async def put_quarter_note(
    year_number: int,
    q: int,
    body: QuarterNoteWrite,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    year = await _get_or_create_year(session, user.id, year_number)
    note = await _get_note(session, year.id, q)

    if note is None:
        note = QuarterNote(year_id=year.id, quarter=q, content=body.content)
        session.add(note)
    else:
        note.content = body.content

    await session.commit()
    await session.refresh(note)
    return QuarterNoteRead(id=note.id, quarter=q, content=note.content)


async def _get_or_create_year(session: AsyncSession, user_id: UUID, year_number: int) -> Year:
    stmt = select(Year).where(Year.user_id == user_id, Year.year_number == year_number)
    year = (await session.execute(stmt)).scalar_one_or_none()
    if year is None:
        year = await seed_year(session, user_id, year_number)
    return year


async def _get_note(session: AsyncSession, year_id: UUID, quarter: int) -> QuarterNote | None:
    stmt = select(QuarterNote).where(
        QuarterNote.year_id == year_id, QuarterNote.quarter == quarter
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _week_brief(w: Week) -> dict:
    marks = [m for m in w.marks if not m.is_deleted]
    tasks = [t for t in w.week_tasks if not t.is_deleted]
    mark_theme_map = {m.id: (m.theme.color if m.theme else None) for m in marks}
    return {
        "id": w.id,
        "iso_week": w.iso_week,
        "display_position": w.display_position,
        "quarter": w.quarter,
        "is_rest_week": w.is_rest_week,
        "cached_load": w.cached_load,
        "marks_preview": [
            {
                "id": m.id,
                "title": m.title,
                "color": m.theme.color if m.theme else None,
            }
            for m in marks[:5]
        ],
        "tasks_preview": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "mark_id": t.mark_id,
                "theme_color": mark_theme_map.get(t.mark_id) if t.mark_id else None,
            }
            for t in tasks[:6]
        ],
    }
