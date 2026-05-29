from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.db import get_async_session
from app.models import Theme, User
from app.schemas.theme import ThemeCreate, ThemeRead, ThemeUpdate

router = APIRouter(prefix="/api/v1", tags=["themes"])


@router.get("/themes", response_model=list[ThemeRead])
async def list_themes(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Theme).where(Theme.user_id == user.id, Theme.is_deleted == False)
    )
    return result.scalars().all()


@router.post("/themes", response_model=ThemeRead)
async def create_theme(
    body: ThemeCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    theme = Theme(user_id=user.id, name=body.name, color=body.color)
    session.add(theme)
    await session.commit()
    await session.refresh(theme)
    return theme


@router.patch("/themes/{theme_id}", response_model=ThemeRead)
async def update_theme(
    theme_id: str,
    body: ThemeUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    theme = await session.get(Theme, theme_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(theme, k, v)
    await session.commit()
    await session.refresh(theme)
    return theme


@router.delete("/themes/{theme_id}")
async def delete_theme(
    theme_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    theme = await session.get(Theme, theme_id)
    theme.is_deleted = True
    theme.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True}
