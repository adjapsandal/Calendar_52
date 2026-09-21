from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.core.ownership import get_owned_mark, get_owned_week
from app.models import DayTask, TaskStatus, User, Week, WeekMark, WeekTask
from app.schemas.week import WeekMarkCreate, WeekMarkRead, WeekMarkUpdate

router = APIRouter(prefix="/api/v1", tags=["marks"])


@router.post("/weeks/{week_id}/marks", response_model=WeekMarkRead)
async def create_mark(
    week_id: str,
    body: WeekMarkCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    week = await get_owned_week(session, week_id, user)

    result = await session.execute(
        select(func.count()).where(WeekMark.week_id == week.id, WeekMark.is_deleted == False)
    )
    pos = result.scalar() or 0

    mark = WeekMark(
        week_id=week.id,
        title=body.title,
        theme_id=body.theme_id,
        description=body.description,
        position=pos,
    )
    session.add(mark)
    await session.commit()
    await session.refresh(mark)
    return mark


@router.patch("/marks/{mark_id}", response_model=WeekMarkRead)
async def update_mark(
    mark_id: str,
    body: WeekMarkUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    mark = await get_owned_mark(session, mark_id, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(mark, k, v)
    await session.commit()
    await session.refresh(mark)
    return mark


@router.delete("/marks/{mark_id}")
async def delete_mark(
    mark_id: str,
    cascade: str = Query("detach", enum=["delete", "detach"]),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    mark = await get_owned_mark(session, mark_id, user)
    now = datetime.now(UTC)
    mark.is_deleted = True
    mark.deleted_at = now

    if cascade == "delete":
        tasks = (await session.execute(
            select(WeekTask).where(WeekTask.mark_id == mark.id, WeekTask.is_deleted == False)
        )).scalars().all()
        for t in tasks:
            t.is_deleted = True
            t.deleted_at = now
            dts = (await session.execute(
                select(DayTask).where(DayTask.week_task_id == t.id, DayTask.is_deleted == False)
            )).scalars().all()
            for dt in dts:
                dt.is_deleted = True
                dt.deleted_at = now
    else:
        await session.execute(
            WeekTask.__table__.update().where(WeekTask.mark_id == mark.id).values(mark_id=None)
        )

    await _recalc_load(session, mark.week_id)
    await session.commit()
    return {"ok": True}


@router.patch("/marks/{mark_id}/move", response_model=WeekMarkRead)
async def move_mark(
    mark_id: str,
    body: dict,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    mark = await get_owned_mark(session, mark_id, user)
    target_week_id = body.get("target_week_id")
    if not target_week_id:
        raise HTTPException(400, "target_week_id required")

    # Целевая неделя тоже должна принадлежать пользователю, иначе можно
    # перенести свою пометку в чужой план.
    target_week = await get_owned_week(session, target_week_id, user)

    old_week_id = mark.week_id
    mark.week_id = target_week.id

    tasks = (await session.execute(
        select(WeekTask).where(WeekTask.mark_id == mark.id, WeekTask.is_deleted == False)
    )).scalars().all()
    for t in tasks:
        old_task_week = t.week_id
        t.week_id = target_week.id
        dts = (await session.execute(
            select(DayTask).where(DayTask.week_task_id == t.id, DayTask.is_deleted == False)
        )).scalars().all()
        for dt in dts:
            dt.week_id = target_week.id
        await _recalc_load(session, old_task_week)

    await _recalc_load(session, old_week_id)
    await _recalc_load(session, mark.week_id)
    await session.commit()
    await session.refresh(mark)
    return mark


async def _recalc_load(session: AsyncSession, week_id):
    result = await session.execute(
        select(func.count()).where(
            WeekTask.week_id == week_id,
            WeekTask.is_deleted == False,
            WeekTask.status == TaskStatus.todo.value,
        )
    )
    load = result.scalar() or 0
    week = await session.get(Week, week_id)
    week.cached_load = load
