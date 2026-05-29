from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
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
    result = await session.execute(
        select(func.count()).where(
            DayTask.week_id == week_id,
            DayTask.day_of_week == day,
            DayTask.is_deleted == False,
        )
    )
    pos = result.scalar() or 0

    task = DayTask(
        week_id=week_id, day_of_week=day, title=body.title,
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
    task = await session.get(DayTask, task_id)
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
    task = await session.get(DayTask, task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(404, "Задача не найдена")
    task.week_id = body["target_week_id"]
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/day-tasks/{task_id}")
async def delete_day_task(
    task_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    task = await session.get(DayTask, task_id)
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True}
