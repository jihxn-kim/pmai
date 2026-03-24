import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class AIReviewType(str, enum.Enum):
    code_review = "code_review"
    analysis = "analysis"
    test_scenario = "test_scenario"


class AIReviewStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pull_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pull_requests.id"), nullable=True)
    type: Mapped[AIReviewType] = mapped_column(Enum(AIReviewType))
    status: Mapped[AIReviewStatus] = mapped_column(Enum(AIReviewStatus), default=AIReviewStatus.pending)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list)
    github_comment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
