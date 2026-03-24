import uuid
from datetime import datetime, date
import enum

from sqlalchemy import Date, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class BriefingStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class WeeklyBriefing(Base):
    __tablename__ = "weekly_briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    org_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    project_briefings: Mapped[dict] = mapped_column(JSONB, default=list)
    status: Mapped[BriefingStatus] = mapped_column(Enum(BriefingStatus), default=BriefingStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
