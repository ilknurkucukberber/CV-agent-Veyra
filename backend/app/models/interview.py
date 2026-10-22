from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin


class InterviewSession(CreatedAtMixin, Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL")
    )
    resume_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL")
    )
    job_posting_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id", ondelete="SET NULL")
    )
    session_type: Mapped[str] = mapped_column(String(50), default="behavioral", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="prepared", nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewAnswer.order_index",
    )
    job_posting: Mapped["JobPosting | None"] = relationship()  # noqa: F821


class InterviewAnswer(CreatedAtMixin, Base):
    """Üretilen bir görüşme sorusu ve (varsa) kullanıcının cevabı."""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(20))
    star_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    # Değerlendirme sonucu (AnswerEvaluation şeması)
    evaluation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped["InterviewSession"] = relationship(back_populates="answers")
