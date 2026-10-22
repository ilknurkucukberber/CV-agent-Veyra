from datetime import datetime

from app.models.enums import ApplicationStatus
from app.schemas.base import APISchema, ORMSchema


class ApplicationBase(APISchema):
    company: str
    position: str
    job_posting_id: int | None = None
    resume_version_id: int | None = None
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_at: datetime | None = None
    interview_at: datetime | None = None
    notes: str | None = None
    interview_notes: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(APISchema):
    company: str | None = None
    position: str | None = None
    job_posting_id: int | None = None
    resume_version_id: int | None = None
    status: ApplicationStatus | None = None
    applied_at: datetime | None = None
    interview_at: datetime | None = None
    notes: str | None = None
    interview_notes: str | None = None


class ApplicationResponse(ORMSchema, ApplicationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class FunnelStage(APISchema):
    key: str
    label: str
    count: int


class FunnelConversion(APISchema):
    from_key: str
    to_key: str
    from_label: str
    to_label: str
    rate: float | None


class ApplicationFunnel(APISchema):
    stages: list[FunnelStage]
    conversions: list[FunnelConversion]
    rejected_count: int
    total_count: int
    note: str = (
        "Huni, her başvurunun GÜNCEL durumuna dayanır (geçmiş durum değişiklikleri "
        "ayrıca kaydedilmiyor); bu yüzden bir aşamayı 'geçti' saymak, o veya daha "
        "ileri bir durumda olmak anlamına gelir. Reddedilen başvurular hangi "
        "aşamada kaybedildiği bilinmediği için huniye dahil edilmez, ayrı sayılır."
    )
