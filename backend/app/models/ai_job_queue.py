import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class JobType(str, enum.Enum):
    code_review = "code_review"
    analysis = "analysis"
    briefing = "briefing"
    test_scenario = "test_scenario"


class JobTrigger(str, enum.Enum):
    webhook = "webhook"
    schedule = "schedule"
    manual = "manual"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AIJobQueue(Base):
    __tablename__ = "ai_job_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType))
    trigger: Mapped[JobTrigger] = mapped_column(Enum(JobTrigger))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    ai_review_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_reviews.id"), nullable=True)
    briefing_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("weekly_briefings.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
