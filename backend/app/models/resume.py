from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EditLevel, ParseStatus
from app.models.mixins import CreatedAtMixin, TimestampMixin


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(100))
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    structure_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, name="parse_status", values_callable=lambda e: [m.value for m in e]),
        default=ParseStatus.PENDING,
        nullable=False,
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(8))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="resumes")  # noqa: F821
    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersion.version_number",
    )


class ResumeVersion(CreatedAtMixin, Base):
    __tablename__ = "resume_versions"
    __table_args__ = (UniqueConstraint("resume_id", "version_number", name="uq_resume_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_posting_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id", ondelete="SET NULL")
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    edit_level: Mapped[EditLevel] = mapped_column(
        Enum(EditLevel, name="edit_level", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    change_log: Mapped[list[Any] | None] = mapped_column(JSONB)
    change_summary: Mapped[str | None] = mapped_column(Text)

    resume: Mapped["Resume"] = relationship(back_populates="versions")
    job_posting: Mapped["JobPosting | None"] = relationship()  # noqa: F821
