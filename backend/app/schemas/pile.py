from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PileItemCreate(BaseModel):
    content: str


class PileItemUpdate(BaseModel):
    content: str


class PileItemRead(BaseModel):
    id: UUID
    content: str
    distributed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DistributeRequest(BaseModel):
    pile_item_ids: list[UUID] | None = None


class DistributionSuggestion(BaseModel):
    pile_item_id: UUID
    target_week_id: UUID
    as_mark: bool
    title: str
    theme_id: UUID | None = None
    reasoning: str
    day_of_week: int = -1
    item_type: str | None = None


class DistributeResponse(BaseModel):
    suggestions: list[DistributionSuggestion]


class ApplySuggestion(BaseModel):
    pile_item_id: UUID
    target_week_id: UUID
    as_mark: bool
    title: str
    theme_id: UUID | None = None
    day_of_week: int = -1


class ApplyRequest(BaseModel):
    items: list[ApplySuggestion]
