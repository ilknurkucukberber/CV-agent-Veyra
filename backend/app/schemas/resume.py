from datetime import datetime
from typing import Any

from app.models.enums import EditLevel, ParseStatus
from app.schemas.ats import AtsAnalysisResponse
from app.schemas.base import APISchema, ORMSchema


# --- Resume ---


class ResumeBase(APISchema):
    title: str
    language: str | None = None
    is_primary: bool = False


class ResumeUpdate(APISchema):
    title: str | None = None
    language: str | None = None
    is_primary: bool | None = None


class ResumeUploadResponse(ORMSchema):
    id: int
    title: str
    original_filename: str | None
    content_type: str | None
    parse_status: ParseStatus
    created_at: datetime


class ResumeStatusResponse(ORMSchema):
    id: int
    parse_status: ParseStatus
    parse_error: str | None
    updated_at: datetime


class ResumeShareResponse(APISchema):
    token: str
    revoked: bool
    created_at: datetime


class PublicResumeShareView(APISchema):
    """Girişsiz, salt-okunur paylaşım görünümü — düzenleme yeteneği yok."""

    resume_title: str
    parsed_json: dict[str, Any] | None
    latest_ats_analysis: AtsAnalysisResponse | None
    shared_at: datetime


class ResumeSummaryResponse(ORMSchema):
    """CV listeleme görünümü için hafif özet (parsed_json/raw_text içermez)."""

    id: int
    title: str
    original_filename: str | None
    content_type: str | None
    parse_status: ParseStatus
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ResumeResponse(ORMSchema, ResumeBase):
    id: int
    user_id: int
    original_filename: str | None
    content_type: str | None
    file_path: str | None
    parse_status: ParseStatus
    parse_error: str | None
    parsed_json: dict[str, Any] | None
    structure_analysis: dict[str, Any] | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime


# --- ResumeVersion ---


class ChangeLogEntrySchema(APISchema):
    section: str
    before: str
    after: str
    reason: str


class RewriteRequest(APISchema):
    edit_level: EditLevel
    target_job_posting_id: int | None = None


class ResumeVersionUpdate(APISchema):
    content: dict[str, Any] | None = None
    change_summary: str | None = None


class ResumeVersionResponse(ORMSchema):
    id: int
    resume_id: int
    version_number: int
    edit_level: EditLevel
    content: dict[str, Any] | None
    change_log: list[ChangeLogEntrySchema] | None
    change_summary: str | None
    job_posting_id: int | None
    created_at: datetime
