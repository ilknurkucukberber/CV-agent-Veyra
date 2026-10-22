from datetime import datetime

from app.agents.ats_analyzer import DISCLAIMER
from app.schemas.base import APISchema, ORMSchema


class AtsAnalysisRequest(APISchema):
    job_posting_id: int | None = None


class AtsGapSchema(APISchema):
    issue: str
    why_it_matters: str
    how_to_fix: str


class AtsAnalysisResponse(ORMSchema):
    id: int
    resume_id: int
    job_posting_id: int | None
    total_score: int
    category_scores: dict[str, int]
    strengths: list[str]
    gaps: list[AtsGapSchema]
    disclaimer: str = DISCLAIMER
    created_at: datetime
