from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.core.ownership import get_owned_day_task, get_owned_week
from app.models import DayTask, User
from app.schemas.week import DayTaskCreate, DayTaskRead, DayTaskUpdate

router = APIRouter(prefix="/api/v1", tags=["day-tasks"])


@router.post("/weeks/{week_id}/days/{day}/tasks", response_model=DayTaskRead)
async def create_day_task(
    week_id: str,
    day: int,
    body: DayTaskCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    week = await get_owned_week(session, week_id, user)
    if not 0 <= day <= 6:
        raise HTTPException(422, "day_of_week должен быть в диапазоне 0..6")

    result = await session.execute(
        select(func.count()).where(
            DayTask.week_id == week.id,
            DayTask.day_of_week == day,
            DayTask.is_deleted == False,
        )
    )
    pos = result.scalar() or 0

    task = DayTask(
        week_id=week.id, day_of_week=day, title=body.title,
        week_task_id=body.week_task_id, position=pos,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/day-tasks/{task_id}", response_model=DayTaskRead)
async def update_day_task(
    task_id: str,
    body: DayTaskUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await get_owned_day_task(session, task_id, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/day-tasks/{task_id}/move", response_model=DayTaskRead)
async def move_day_task(
    task_id: str,
    body: dict,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await get_owned_day_task(session, task_id, user)
    target_week_id = body.get("target_week_id")
    if not target_week_id:
        raise HTTPException(400, "target_week_id required")

    target_week = await get_owned_week(session, target_week_id, user)
    task.week_id = target_week.id
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/day-tasks/{task_id}")
async def delete_day_task(
    task_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await get_owned_day_task(session, task_id, user)
    task.is_deleted = True
    task.deleted_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}
