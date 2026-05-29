from datetime import datetime
from enum import IntEnum
from uuid import UUID

from pydantic import BaseModel


class DistributionDepth(IntEnum):
    STRATEGIC = 1   # Лёгкий — только пометки
    TACTICAL = 2    # Средний — пометки + задачи недели
    DETAILED = 3    # Подробный — пометки + задачи недели + задачи дня


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
    depth: DistributionDepth = DistributionDepth.TACTICAL


class DistributionSuggestion(BaseModel):
    pile_item_id: UUID
    target_week_id: UUID
    as_mark: bool
    title: str
    theme_id: UUID | None = None
    reasoning: str
    day_of_week: int = -1
    item_type: str = "week_task"  # "mark" | "week_task" | "day_task"
    index: int = 0
    parent_index: int = -1  # -1 = root (mark)


class DistributeResponse(BaseModel):
    suggestions: list[DistributionSuggestion]


class ApplySuggestion(BaseModel):
    pile_item_id: UUID
    target_week_id: UUID
    as_mark: bool
    title: str
    theme_id: UUID | None = None
    day_of_week: int = -1
    item_type: str = "week_task"
    index: int = 0
    parent_index: int = -1


class ApplyRequest(BaseModel):
    items: list[ApplySuggestion]
