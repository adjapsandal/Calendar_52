from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.core.ownership import get_owned_week, get_owned_week_task
from app.models import TaskStatus, User, Week, WeekTask
from app.schemas.week import WeekTaskCreate, WeekTaskRead, WeekTaskUpdate

router = APIRouter(prefix="/api/v1", tags=["week-tasks"])


@router.post("/weeks/{week_id}/tasks", response_model=WeekTaskRead)
async def create_week_task(
    week_id: str,
    body: WeekTaskCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    week = await get_owned_week(session, week_id, user)

    result = await session.execute(
        select(func.count()).where(WeekTask.week_id == week.id, WeekTask.is_deleted == False)
    )
    pos = result.scalar() or 0

    task = WeekTask(
        week_id=week.id, title=body.title, mark_id=body.mark_id,
        theme_id=body.theme_id, position=pos,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    await _recalc_load(session, week.id)
    await session.commit()

    return task


@router.patch("/week-tasks/{task_id}", response_model=WeekTaskRead)
async def update_week_task(
    task_id: str,
    body: WeekTaskUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await get_owned_week_task(session, task_id, user)
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
    task = await get_owned_week_task(session, task_id, user)
    task.is_deleted = True
    task.deleted_at = datetime.now(UTC)
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
    task = await get_owned_week_task(session, task_id, user)
    target_week_id = body.get("target_week_id")
    if not target_week_id:
        raise HTTPException(400, "target_week_id required")

    target_week = await get_owned_week(session, target_week_id, user)

    old_week_id = task.week_id
    task.week_id = target_week.id
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
