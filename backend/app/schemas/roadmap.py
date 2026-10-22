from datetime import datetime

from pydantic import Field

from app.schemas.base import APISchema, ORMSchema


class DevelopmentStepSchema(APISchema):
    step: int
    action: str
    estimated_effort: str


class RoadmapProgressUpdate(APISchema):
    """Tamamlanan adımları günceller (tam liste olarak gönderilir)."""

    completed_steps: list[int] = Field(default_factory=list)


class CareerRoadmapResponse(ORMSchema):
    id: int
    target_role: str
    resume_id: int | None
    resume_version_id: int | None
    job_posting_id: int | None
    current_strengths: list[str]
    gaps: list[str]
    development_plan: list[DevelopmentStepSchema]
    completed_steps: list[int]
    progress_percentage: int
    created_at: datetime
    updated_at: datetime
