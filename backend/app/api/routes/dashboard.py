from typing import Any

from sqlalchemy import select, func, desc

from app.api.deps import CurrentUser, DbSession
from app.models.profile import Profile
from app.models.ats import AtsAnalysis
from app.models.resume import Resume, ResumeVersion
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.schemas.dashboard import DashboardSummary
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(current_user: CurrentUser, db: DbSession) -> Any:
    """
    Kullanıcının dashboard özet bilgilerini döndürür.
    """
    summary = DashboardSummary()

    # 1. Profile Completion Percentage
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    profile = db.scalars(stmt).first()

    if profile:
        fields_to_check = [
            "education_level", "department", "university", "graduation_year",
            "work_experience", "technical_skills", "english_level",
            "work_mode_preference", "career_goal"
        ]
        filled = sum(1 for field in fields_to_check if getattr(profile, field))
        summary.profile_completion_percentage = int((filled / len(fields_to_check)) * 100)
    else:
        summary.profile_completion_percentage = 0

    # 2. Last ATS Score
    stmt = (
        select(AtsAnalysis.ats_score)
        .join(Resume, Resume.id == AtsAnalysis.resume_id)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(AtsAnalysis.created_at))
        .limit(1)
    )
    summary.ats_score = db.scalar(stmt)

    # 3. CV Version Count
    stmt = (
        select(func.count(ResumeVersion.id))
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(Resume.user_id == current_user.id)
    )
    summary.cv_version_count = db.scalar(stmt) or 0

    # 4. Applications Count and Status Distribution
    stmt = select(Application).where(Application.user_id == current_user.id)
    applications = list(db.scalars(stmt).all())

    summary.active_applications_count = len(applications)

    status_counts = {}
    upcoming_interviews = []

    for app in applications:
        status = app.status.value if hasattr(app.status, 'value') else app.status
        status_counts[status] = status_counts.get(status, 0) + 1

        # 5. Upcoming Interviews
        if status in [ApplicationStatus.HR_INTERVIEW.value, ApplicationStatus.TECHNICAL_INTERVIEW.value]:
            upcoming_interviews.append({
                "id": app.id,
                "company": app.company,
                "position": app.position,
                "status": status,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None
            })

    summary.status_distribution = status_counts
    summary.upcoming_interviews = upcoming_interviews

    return summary
