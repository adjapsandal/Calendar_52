from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskStatusItem(BaseModel):
    id: UUID
    status: str


class ReflectRequest(BaseModel):
    task_statuses: list[TaskStatusItem] = []
    raw_input: str | None = None


class ReviewRead(BaseModel):
    id: UUID
    week_id: UUID
    raw_input: str
    achievements: str
    lessons: str
    corrections: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkBrief(BaseModel):
    id: UUID
    title: str


class TaskBrief(BaseModel):
    id: UUID
    title: str
    status: str
    mark_id: UUID | None = None


class ReviewStartResponse(BaseModel):
    week_id: UUID
    display_position: int
    marks: list[MarkBrief]
    tasks: list[TaskBrief]
    existing_review: ReviewRead | None = None


class ReviewCompleteResponse(BaseModel):
    ok: bool
    cancelled_count: int
