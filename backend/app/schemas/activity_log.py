import uuid
from datetime import datetime

from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    detail: dict
    created_at: datetime

    model_config = {"from_attributes": True}
