from datetime import datetime

from pydantic import model_validator

from app.schemas.base import APISchema, ORMSchema


# --- JobPosting ---


class JobRequirementsSchema(APISchema):
    required_skills: list[str]
    preferred_skills: list[str]
    experience_years: str | None
    programming_languages: list[str]
    tools_and_technologies: list[str]
    education_requirement: str | None
    language_requirement: str | None
    key_responsibilities: list[str]


class JobPostingCreate(APISchema):
    """İlan metni yapıştırılarak ya da URL verilerek oluşturulur."""

    raw_text: str | None = None
    url: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None

    @model_validator(mode="after")
    def require_text_or_url(self) -> "JobPostingCreate":
        if not (self.raw_text and self.raw_text.strip()) and not (self.url and self.url.strip()):
            raise ValueError("raw_text veya url alanlarından biri zorunludur.")
        return self


class JobPostingResponse(ORMSchema):
    id: int
    user_id: int
    title: str
    company: str | None
    location: str | None
    url: str | None
    raw_text: str | None
    requirements: JobRequirementsSchema | None
    created_at: datetime


# --- JobMatch ---


class ImprovementSuggestionSchema(APISchema):
    suggestion: str
    reason: str


class JobMatchResponse(ORMSchema):
    id: int
    job_posting_id: int
    resume_id: int
    resume_version_id: int | None
    match_percentage: int
    matched_skills: list[str]
    missing_skills: list[str]
    improvement_suggestions: list[ImprovementSuggestionSchema]
    created_at: datetime
