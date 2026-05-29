from uuid import UUID

from pydantic import BaseModel


class MarkPreview(BaseModel):
    id: UUID
    title: str
    color: str | None = None

    model_config = {"from_attributes": True}


class TaskPreview(BaseModel):
    id: UUID
    title: str
    status: str
    mark_id: UUID | None = None
    theme_color: str | None = None

    model_config = {"from_attributes": True}


class WeekBrief(BaseModel):
    id: UUID
    iso_week: int
    display_position: int
    quarter: int
    is_rest_week: bool
    cached_load: int
    marks_preview: list[MarkPreview] = []
    tasks_preview: list[TaskPreview] = []

    model_config = {"from_attributes": True}


class QuarterNoteRead(BaseModel):
    id: UUID | None = None
    quarter: int
    content: str

    model_config = {"from_attributes": True}


class QuarterNoteWrite(BaseModel):
    content: str


class QuarterBlock(BaseModel):
    quarter: int
    weeks: list[WeekBrief]
    note: QuarterNoteRead | None


class YearRead(BaseModel):
    id: UUID
    year_number: int
    quarters: list[QuarterBlock]

    model_config = {"from_attributes": True}
