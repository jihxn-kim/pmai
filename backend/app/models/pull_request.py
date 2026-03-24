import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PRState(str, enum.Enum):
    open = "open"
    merged = "merged"
    closed = "closed"


class ReviewState(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        Index("ix_pull_requests_project_id_state", "project_id", "state"),
        UniqueConstraint("project_id", "github_pr_id", name="uq_pull_requests_project_github_pr"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    github_pr_id: Mapped[int] = mapped_column(Integer, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[PRState] = mapped_column(
        Enum(PRState, name="prstate"), nullable=False, default=PRState.open
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    review_state: Mapped[ReviewState | None] = mapped_column(
        Enum(ReviewState, name="reviewstate"), nullable=True
    )
    base_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    head_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="pull_requests"
    )
    author: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[author_id]
    )
    reviewers: Mapped[list["PullRequestReviewer"]] = relationship(
        "PullRequestReviewer", back_populates="pull_request", cascade="all, delete-orphan"
    )


class PullRequestReviewer(Base):
    __tablename__ = "pull_request_reviewers"

    pr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, name="reviewstate"),
        nullable=False,
        default=ReviewState.pending,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="reviewers"
    )
    user: Mapped["User"] = relationship("User")  # noqa: F821
