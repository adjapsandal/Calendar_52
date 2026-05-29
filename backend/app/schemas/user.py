from uuid import UUID

from fastapi_users import schemas
from pydantic import EmailStr


class UserRead(schemas.BaseUser[UUID]):
    timezone: str
    onboarded: bool


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    timezone: str | None = None
    onboarded: bool | None = None
