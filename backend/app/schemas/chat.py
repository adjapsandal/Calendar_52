from uuid import UUID

from pydantic import BaseModel


class ChatOperation(BaseModel):
    action: str  # "move" | "delete" | "create" | "update_status"
    item_type: str  # "week_task" | "day_task" | "mark"
    item_id: str | None = None
    item_title: str
    target_week_id: UUID | None = None
    new_status: str | None = None
    day_of_week: int = -1
    reasoning: str = ""


class ChatResponse(BaseModel):
    reply: str
    operations: list[ChatOperation] | None = None
