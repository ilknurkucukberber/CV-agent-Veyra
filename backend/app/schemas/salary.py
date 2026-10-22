from datetime import datetime
from typing import Any

from app.schemas.base import APISchema, ORMSchema


class SalaryReportBase(APISchema):
    job_title: str
    location: str | None = None
    experience_years: int | None = None
    currency: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_median: int | None = None
    data: dict[str, Any] | None = None


class SalaryReportCreate(SalaryReportBase):
    pass


class SalaryReportUpdate(APISchema):
    location: str | None = None
    experience_years: int | None = None
    currency: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_median: int | None = None
    data: dict[str, Any] | None = None


class SalaryReportResponse(ORMSchema, SalaryReportBase):
    id: int
    user_id: int
    created_at: datetime


class SalaryEstimateRequest(APISchema):
    position: str
    city: str
    experience_level: str
    work_mode: str | None = None
    skills: list[str] | None = None
    education_level: str | None = None

class SalaryEstimateResponse(APISchema):
    range_low: int
    range_mid: int
    range_high: int
    currency: str
    source: str
    source_date: str
    disclaimer: str = (
        "Bu değerler, harici bir kıyaslama raporuna değil, CV Agent'ın kendi "
        "derlediği yaklaşık iç referans tablosuna dayanır; resmi/doğrulanmış bir "
        "piyasa araştırması değildir. Şirket, sektör, yan haklar, çalışma modeli "
        "ve adayın teknik seviyesine göre gerçek rakamlar önemli ölçüde değişebilir."
    )
