from typing import Any
from app.schemas.base import APISchema

class DashboardSummary(APISchema):
    ats_score: float | None = None
    active_applications_count: int = 0
    status_distribution: dict[str, int] = {}
    cv_version_count: int = 0
    upcoming_interviews: list[dict[str, Any]] = []
    profile_completion_percentage: int = 0
