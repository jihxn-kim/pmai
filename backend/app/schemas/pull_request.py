import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.pull_request import PRState, ReviewState


class PRResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    github_pr_id: int
    number: int
    title: str
    state: PRState
    author_id: uuid.UUID | None
    review_state: ReviewState | None
    merged_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
