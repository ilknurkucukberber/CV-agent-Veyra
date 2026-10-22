from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    # Claude ile çıkarılmış yapılandırılmış gereksinimler (JobRequirements şeması)
    requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(8))
    source: Mapped[str | None] = mapped_column(String(100))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    matches: Mapped[list["JobMatch"]] = relationship(
        back_populates="job_posting", cascade="all, delete-orphan"
    )


class JobMatch(CreatedAtMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint(
            "resume_version_id",
            "job_posting_id",
            name="uq_job_match_version_posting",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True
    )
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_score: Mapped[float | None] = mapped_column(Float)
    matched_skills: Mapped[list[Any] | None] = mapped_column(JSONB)
    missing_skills: Mapped[list[Any] | None] = mapped_column(JSONB)
    improvement_suggestions: Mapped[list[Any] | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)

    resume: Mapped["Resume"] = relationship()  # noqa: F821
    resume_version: Mapped["ResumeVersion | None"] = relationship()  # noqa: F821
    job_posting: Mapped["JobPosting"] = relationship(back_populates="matches")

    @property
    def match_percentage(self) -> int:
        return int(self.match_score or 0)
