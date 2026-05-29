from uuid import UUID

from pydantic import BaseModel


class ThemeCreate(BaseModel):
    name: str
    color: str


class ThemeUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class ThemeRead(BaseModel):
    id: UUID
    name: str
    color: str

    model_config = {"from_attributes": True}
