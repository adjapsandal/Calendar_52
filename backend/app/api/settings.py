from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import Settings, User
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings", response_model=SettingsRead)
async def get_settings(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(Settings).where(Settings.user_id == user.id)
    settings = (await session.execute(stmt)).scalar_one()
    return settings


@router.patch("/settings", response_model=SettingsRead)
async def update_settings(
    body: SettingsUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(Settings).where(Settings.user_id == user.id)
    settings = (await session.execute(stmt)).scalar_one()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(settings, k, v)
    await session.commit()
    await session.refresh(settings)
    return settings
