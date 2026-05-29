from uuid import UUID

from pydantic import BaseModel


class SettingsRead(BaseModel):
    user_id: UUID
    week_budget: int
    rest_mode: str
    hard_protection: bool

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    week_budget: int | None = None
    rest_mode: str | None = None
    hard_protection: bool | None = None
