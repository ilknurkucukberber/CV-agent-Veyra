from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.agents.job_matcher import JobAgentError, extract_requirements, match_resume_to_job
from app.api.deps import CurrentUser, DbSession, Language
from app.core.pagination import Offset, OptionalLimit, paginate
from app.models import JobMatch, JobPosting, Resume, ResumeVersion
from app.schemas.job import JobMatchResponse, JobPostingCreate, JobPostingResponse
from app.services.url_fetch import UrlFetchError, fetch_job_text

router = APIRouter(prefix="/job-postings", tags=["job-postings"])

MIN_JOB_TEXT_LENGTH = 50


def _get_owned_posting_or_404(
    db: DbSession, user_id: int, job_posting_id: int
) -> JobPosting:
    posting = db.scalar(
        select(JobPosting).where(
            JobPosting.id == job_posting_id, JobPosting.user_id == user_id
        )
    )
    if posting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı")
    return posting


@router.post("", response_model=JobPostingResponse, status_code=status.HTTP_201_CREATED)
def create_job_posting(
    payload: JobPostingCreate, current_user: CurrentUser, db: DbSession, language: Language
) -> JobPosting:
    if payload.raw_text and payload.raw_text.strip():
        job_text = payload.raw_text.strip()
    else:
        try:
            job_text = fetch_job_text(payload.url.strip())
        except UrlFetchError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if len(job_text) < MIN_JOB_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="İlan metni çok kısa; analiz için yeterli içerik yok.",
        )

    try:
        requirements = extract_requirements(job_text, language=language)
    except JobAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    posting = JobPosting(
        user_id=current_user.id,
        title=payload.title or "İsimsiz pozisyon",
        company=payload.company,
        location=payload.location,
        url=payload.url,
        raw_text=job_text,
        description=job_text,
        requirements=requirements.model_dump(),
        source="url" if payload.url else "manual",
    )
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


@router.get("", response_model=list[JobPostingResponse])
def list_job_postings(
    current_user: CurrentUser, db: DbSession, limit: OptionalLimit = None, offset: Offset = 0
) -> list[JobPosting]:
    stmt = (
        select(JobPosting)
        .where(JobPosting.user_id == current_user.id)
        .order_by(JobPosting.created_at.desc())
    )
    return list(db.scalars(paginate(stmt, limit, offset)))


@router.get("/{job_posting_id}", response_model=JobPostingResponse)
def get_job_posting(
    job_posting_id: int, current_user: CurrentUser, db: DbSession
) -> JobPosting:
    return _get_owned_posting_or_404(db, current_user.id, job_posting_id)


@router.post(
    "/{job_posting_id}/match",
    response_model=JobMatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def match_job_posting(
    job_posting_id: int,
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
    resume_version_id: int | None = Query(default=None),
    resume_id: int | None = Query(default=None),
) -> JobMatch:
    posting = _get_owned_posting_or_404(db, current_user.id, job_posting_id)

    if resume_version_id is None and resume_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_version_id veya resume_id parametrelerinden biri zorunludur.",
        )

    version: ResumeVersion | None = None
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
        resume = db.get(Resume, version.resume_id)
        content = version.content
    else:
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

    if not content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV içeriği boş; önce CV'nin ayrıştırılmasını bekleyin.",
        )

    try:
        result = match_resume_to_job(
            content, posting.title, posting.requirements, posting.description, language=language
        )
    except JobAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    existing = db.scalar(
        select(JobMatch).where(
            JobMatch.job_posting_id == posting.id,
            JobMatch.resume_version_id == (version.id if version else None),
            JobMatch.resume_id == resume.id,
        )
    )
    match = existing or JobMatch(
        resume_id=resume.id,
        resume_version_id=version.id if version else None,
        job_posting_id=posting.id,
    )
    match.match_score = result.match_percentage
    match.matched_skills = result.matched_skills
    match.missing_skills = result.missing_skills
    match.improvement_suggestions = [s.model_dump() for s in result.improvement_suggestions]

    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("/{job_posting_id}/matches", response_model=list[JobMatchResponse])
def list_matches(
    job_posting_id: int, current_user: CurrentUser, db: DbSession
) -> list[JobMatch]:
    posting = _get_owned_posting_or_404(db, current_user.id, job_posting_id)
    return list(
        db.scalars(
            select(JobMatch)
            .where(JobMatch.job_posting_id == posting.id)
            .order_by(JobMatch.created_at.desc())
        )
    )
