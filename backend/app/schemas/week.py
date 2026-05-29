from uuid import UUID

from pydantic import BaseModel


class WeekMarkCreate(BaseModel):
    title: str
    theme_id: UUID | None = None
    description: str | None = None


class WeekMarkUpdate(BaseModel):
    title: str | None = None
    theme_id: UUID | None = None
    description: str | None = None
    position: int | None = None


class WeekMarkRead(BaseModel):
    id: UUID
    theme_id: UUID | None = None
    theme_color: str | None = None
    title: str
    description: str | None = None
    position: int

    model_config = {"from_attributes": True}


class WeekTaskCreate(BaseModel):
    title: str
    mark_id: UUID | None = None
    theme_id: UUID | None = None


class WeekTaskUpdate(BaseModel):
    title: str | None = None
    mark_id: UUID | None = None
    theme_id: UUID | None = None
    status: str | None = None
    position: int | None = None


class WeekTaskRead(BaseModel):
    id: UUID
    mark_id: UUID | None = None
    theme_id: UUID | None = None
    title: str
    status: str
    position: int

    model_config = {"from_attributes": True}


class DayTaskCreate(BaseModel):
    title: str
    week_task_id: UUID | None = None


class DayTaskUpdate(BaseModel):
    title: str | None = None
    week_task_id: UUID | None = None
    status: str | None = None
    day_of_week: int | None = None
    position: int | None = None


class DayTaskRead(BaseModel):
    id: UUID
    week_task_id: UUID | None = None
    day_of_week: int
    title: str
    status: str
    position: int

    model_config = {"from_attributes": True}


class WeekDetail(BaseModel):
    id: UUID
    iso_week: int
    display_position: int
    quarter: int
    is_rest_week: bool
    cached_load: int
    year_number: int
    marks: list[WeekMarkRead] = []
    week_tasks: list[WeekTaskRead] = []
    day_tasks: list[DayTaskRead] = []

    model_config = {"from_attributes": True}
