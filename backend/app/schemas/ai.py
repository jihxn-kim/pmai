import uuid
from datetime import datetime, date
from pydantic import BaseModel

from app.models.ai_review import AIReviewType, AIReviewStatus
from app.models.ai_job_queue import JobType, JobTrigger, JobStatus
from app.models.weekly_briefing import BriefingStatus


class JobCreatedResponse(BaseModel):
    job_id: uuid.UUID
    status: str = "queued"
    message: str

class JobStatusResponse(BaseModel):
    id: uuid.UUID
    job_type: JobType
    status: JobStatus
    ai_review_id: uuid.UUID | None
    briefing_id: uuid.UUID | None
    error_message: str | None
    progress_log: list | None = None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}

class AIReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    pull_request_id: uuid.UUID | None
    type: AIReviewType
    status: AIReviewStatus
    summary: str | None
    detail: dict
    suggestions: list
    github_comment_id: int | None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}

class BriefingResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    week_start: date
    org_summary: dict
    project_briefings: list
    status: BriefingStatus
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}

class TestScenarioRequest(BaseModel):
    pr_number: int | None = None
    file_paths: list[str] | None = None
