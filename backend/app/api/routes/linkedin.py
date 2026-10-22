from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.agents.linkedin_optimizer import LinkedInAgentError, optimize_profile
from app.api.deps import CurrentUser, DbSession, Language
from app.models import JobPosting, Resume, ResumeVersion
from app.schemas.linkedin import LinkedInOptimizeResponse

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


@router.post("/optimize", response_model=LinkedInOptimizeResponse)
def optimize_linkedin_profile(
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
    resume_version_id: int | None = Query(default=None),
    resume_id: int | None = Query(default=None),
    target_role: str | None = Query(default=None, max_length=255),
    job_posting_id: int | None = Query(default=None),
) -> LinkedInOptimizeResponse:
    if resume_version_id is not None:
        version = db.scalar(
            select(ResumeVersion)
            .join(Resume, Resume.id == ResumeVersion.resume_id)
            .where(
                ResumeVersion.id == resume_version_id,
                Resume.user_id == current_user.id,
            )
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV versiyonu bulunamadı"
            )
        content = version.content
    elif resume_id is not None:
        resume = db.scalar(
            select(Resume).where(
                Resume.id == resume_id, Resume.user_id == current_user.id
            )
        )
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı"
            )
        content = resume.parsed_json
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_version_id veya resume_id parametrelerinden biri zorunludur.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV içeriği boş; önce CV'nin ayrıştırılmasını bekleyin.",
        )

    job_requirements = None
    if job_posting_id is not None:
        posting = db.scalar(
            select(JobPosting).where(
                JobPosting.id == job_posting_id, JobPosting.user_id == current_user.id
            )
        )
        if posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı"
            )
        job_requirements = posting.requirements

    try:
        result = optimize_profile(content, target_role, job_requirements, language=language)
    except LinkedInAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    return LinkedInOptimizeResponse(**result.model_dump())
