from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.auth import current_active_user
from app.core.db import get_async_session
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
    result = await session.execute(
        select(func.count()).where(WeekMark.week_id == week_id, WeekMark.is_deleted == False)
    )
    pos = result.scalar() or 0

    mark = WeekMark(week_id=week_id, title=body.title, theme_id=body.theme_id, description=body.description, position=pos)
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
    mark = await session.get(WeekMark, mark_id)
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
    from datetime import datetime, timezone

    mark = await session.get(WeekMark, mark_id)
    mark.is_deleted = True
    mark.deleted_at = datetime.now(timezone.utc)

    if cascade == "delete":
        tasks = (await session.execute(
            select(WeekTask).where(WeekTask.mark_id == mark_id, WeekTask.is_deleted == False)
        )).scalars().all()
        for t in tasks:
            t.is_deleted = True
            t.deleted_at = datetime.now(timezone.utc)
        from app.models import DayTask
        for t in tasks:
            dts = (await session.execute(
                select(DayTask).where(DayTask.week_task_id == t.id, DayTask.is_deleted == False)
            )).scalars().all()
            for dt in dts:
                dt.is_deleted = True
                dt.deleted_at = datetime.now(timezone.utc)
    else:
        await session.execute(
            WeekTask.__table__.update().where(WeekTask.mark_id == mark_id).values(mark_id=None)
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
    mark = await session.get(WeekMark, mark_id)
    target_week_id = body.get("target_week_id")
    if not target_week_id:
        from fastapi import HTTPException
        raise HTTPException(400, "target_week_id required")

    old_week_id = mark.week_id
    mark.week_id = UUID(target_week_id)

    tasks = (await session.execute(
        select(WeekTask).where(WeekTask.mark_id == mark_id, WeekTask.is_deleted == False)
    )).scalars().all()
    for t in tasks:
        old_task_week = t.week_id
        t.week_id = UUID(target_week_id)
        dts = (await session.execute(
            select(DayTask).where(DayTask.week_task_id == t.id, DayTask.is_deleted == False)
        )).scalars().all()
        for dt in dts:
            dt.week_id = UUID(target_week_id)
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
