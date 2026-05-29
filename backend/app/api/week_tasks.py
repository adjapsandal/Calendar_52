from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import DayTask, TaskStatus, User, Week, WeekTask
from app.schemas.week import WeekTaskCreate, WeekTaskRead, WeekTaskUpdate

router = APIRouter(prefix="/api/v1", tags=["week-tasks"])


@router.post("/weeks/{week_id}/tasks", response_model=WeekTaskRead)
async def create_week_task(
    week_id: str,
    body: WeekTaskCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(func.count()).where(WeekTask.week_id == week_id, WeekTask.is_deleted == False)
    )
    pos = result.scalar() or 0

    task = WeekTask(
        week_id=week_id, title=body.title, mark_id=body.mark_id,
        theme_id=body.theme_id, position=pos,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    await _recalc_load(session, week_id)
    await session.commit()

    return task


@router.patch("/week-tasks/{task_id}", response_model=WeekTaskRead)
async def update_week_task(
    task_id: str,
    body: WeekTaskUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await session.get(WeekTask, task_id)
    old_status = task.status
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    await session.commit()
    await session.refresh(task)

    if body.status is not None and body.status != old_status:
        await _recalc_load(session, task.week_id)
        await session.commit()

    return task


@router.delete("/week-tasks/{task_id}")
async def delete_week_task(
    task_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await session.get(WeekTask, task_id)
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    await _recalc_load(session, task.week_id)
    await session.commit()
    return {"ok": True}


@router.patch("/week-tasks/{task_id}/move", response_model=WeekTaskRead)
async def move_week_task(
    task_id: str,
    body: dict,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await session.get(WeekTask, task_id)
    target_week_id = body.get("target_week_id")
    if not target_week_id:
        from fastapi import HTTPException
        raise HTTPException(400, "target_week_id required")

    old_week_id = task.week_id
    task.week_id = UUID(target_week_id)
    await _recalc_load(session, old_week_id)
    await _recalc_load(session, task.week_id)
    await session.commit()
    await session.refresh(task)
    return task


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
