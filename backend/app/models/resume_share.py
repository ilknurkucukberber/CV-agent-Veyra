from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin


class ResumeShare(CreatedAtMixin, Base):
    """CV'yi girişsiz, salt-okunur bir link üzerinden (ör. bir mentora)
    paylaşmayı sağlayan token. Paylaşılan görünüm yalnızca CV içeriğini ve en
    güncel ATS analizini gösterir; düzenleme yeteneği hiç sunulmaz."""

    __tablename__ = "resume_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resume: Mapped["Resume"] = relationship()  # noqa: F821
