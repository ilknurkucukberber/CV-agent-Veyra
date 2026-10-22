from typing import Any

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin


class AtsAnalysis(CreatedAtMixin, Base):
    __tablename__ = "ats_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_posting_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id", ondelete="SET NULL")
    )
    ats_score: Mapped[float | None] = mapped_column(Float)
    category_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    strengths: Mapped[list[Any] | None] = mapped_column(JSONB)
    gaps: Mapped[list[Any] | None] = mapped_column(JSONB)
    keyword_matches: Mapped[list[Any] | None] = mapped_column(JSONB)
    missing_keywords: Mapped[list[Any] | None] = mapped_column(JSONB)
    format_issues: Mapped[list[Any] | None] = mapped_column(JSONB)
    suggestions: Mapped[list[Any] | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)

    resume: Mapped["Resume"] = relationship()  # noqa: F821
    job_posting: Mapped["JobPosting | None"] = relationship()  # noqa: F821

    @property
    def total_score(self) -> int:
        return int(self.ats_score or 0)
