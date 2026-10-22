from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WorkModePreference
from app.models.mixins import TimestampMixin


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    education_level: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(255))
    university: Mapped[str | None] = mapped_column(String(255))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    work_experience: Mapped[list[Any] | None] = mapped_column(JSONB)
    internship_experience: Mapped[list[Any] | None] = mapped_column(JSONB)
    technical_skills: Mapped[list[Any] | None] = mapped_column(JSONB)
    certificates: Mapped[list[Any] | None] = mapped_column(JSONB)
    projects: Mapped[list[Any] | None] = mapped_column(JSONB)
    english_level: Mapped[str | None] = mapped_column(String(20))
    target_city: Mapped[str | None] = mapped_column(String(255))
    work_mode_preference: Mapped[WorkModePreference | None] = mapped_column(
        Enum(
            WorkModePreference,
            name="work_mode_preference",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    career_goal: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821
