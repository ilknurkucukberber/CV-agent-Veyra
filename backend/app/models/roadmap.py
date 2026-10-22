from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CareerRoadmap(TimestampMixin, Base):
    __tablename__ = "career_roadmaps"

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
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)

    current_strengths: Mapped[list[Any] | None] = mapped_column(JSONB)
    gaps: Mapped[list[Any] | None] = mapped_column(JSONB)
    development_plan: Mapped[list[Any] | None] = mapped_column(JSONB)
    # İlerleme takibi: tamamlanan adım numaraları (development_plan[].step)
    completed_steps: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    resume_version: Mapped["ResumeVersion | None"] = relationship()  # noqa: F821
    job_posting: Mapped["JobPosting | None"] = relationship()  # noqa: F821

    @property
    def progress_percentage(self) -> int:
        total = len(self.development_plan or [])
        if total == 0:
            return 0
        done = len([s for s in (self.completed_steps or []) if isinstance(s, int)])
        return round(min(done, total) / total * 100)
