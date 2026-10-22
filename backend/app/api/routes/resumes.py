import secrets
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import desc, func, select, update

from app.agents.ats_analyzer import AtsAnalysisError, analyze_resume
from app.agents.cv_writer import CvRewriteError, rewrite_resume
from app.api.deps import CurrentUser, DbSession, Language
from app.core.config import settings
from app.core.llm import LLMConfigurationError, ensure_configured
from app.core.pagination import Offset, OptionalLimit, paginate
from app.models import (
    AtsAnalysis,
    EditLevel,
    JobPosting,
    ParseStatus,
    Profile,
    Resume,
    ResumeShare,
    ResumeVersion,
)
from app.schemas.ats import AtsAnalysisRequest, AtsAnalysisResponse
from app.schemas.resume import (
    PublicResumeShareView,
    ResumeResponse,
    ResumeShareResponse,
    ResumeStatusResponse,
    ResumeSummaryResponse,
    ResumeUpdate,
    ResumeUploadResponse,
    ResumeVersionResponse,
    ResumeVersionUpdate,
    RewriteRequest,
)
from app.services.extraction import ALLOWED_CONTENT_TYPES
from app.services.storage import delete_upload, save_upload
from app.workers.tasks import parse_resume_task

SHARE_TOKEN_BYTES = 24

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)


def _require_parse_service() -> None:
    try:
        ensure_configured()
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _enqueue_parse(db: DbSession, resume: Resume) -> None:
    try:
        parse_resume_task.delay(resume.id)
    except Exception as exc:
        logger.error("CV parse queue unavailable (%s)", type(exc).__name__)
        resume.parse_status = ParseStatus.FAILED
        resume.parse_error = "CV işleme kuyruğuna ulaşılamadı. Lütfen biraz sonra tekrar dene."
        db.commit()
        raise HTTPException(status_code=503, detail=resume.parse_error) from exc

EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _get_owned_resume_or_404(db: DbSession, user_id: int, resume_id: int) -> Resume:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı")
    return resume


@router.post(
    "/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_resume(
    file: UploadFile, current_user: CurrentUser, db: DbSession
) -> Resume:
    filename = file.filename or "cv"
    extension = Path(filename).suffix.lower()
    content_type = EXTENSION_CONTENT_TYPES.get(extension) or file.content_type

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Desteklenmeyen dosya türü. PDF, DOCX, JPG veya PNG yükleyin.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dosya boş")
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dosya {settings.MAX_UPLOAD_MB} MB sınırını aşıyor",
        )

    _require_parse_service()

    file_path = save_upload(content, filename, current_user.id)

    resume = Resume(
        user_id=current_user.id,
        title=Path(filename).stem,
        original_filename=filename,
        file_path=file_path,
        content_type=content_type,
        parse_status=ParseStatus.PENDING,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    _enqueue_parse(db, resume)
    return resume


@router.post("/{resume_id}/retry-parse", response_model=ResumeUploadResponse, status_code=202)
def retry_resume_parse(resume_id: int, current_user: CurrentUser, db: DbSession) -> Resume:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    _require_parse_service()
    result = db.execute(
        update(Resume)
        .where(Resume.id == resume.id, Resume.parse_status == ParseStatus.FAILED)
        .values(parse_status=ParseStatus.PENDING, parse_error=None)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Yalnızca başarısız CV işlemleri yeniden başlatılabilir.")
    db.commit()
    db.refresh(resume)
    _enqueue_parse(db, resume)
    return resume


@router.get("", response_model=list[ResumeSummaryResponse])
def list_resumes(
    current_user: CurrentUser, db: DbSession, limit: OptionalLimit = None, offset: Offset = 0
) -> list[Resume]:
    stmt = (
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.is_primary.desc(), Resume.created_at.desc())
    )
    return list(db.scalars(paginate(stmt, limit, offset)))


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, current_user: CurrentUser, db: DbSession) -> None:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    if resume.file_path:
        delete_upload(resume.file_path)
    db.delete(resume)
    db.commit()


@router.patch("/{resume_id}", response_model=ResumeResponse)
def update_resume(
    resume_id: int,
    payload: ResumeUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Resume:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)

    if payload.is_primary:
        db.execute(
            update(Resume)
            .where(Resume.user_id == current_user.id, Resume.id != resume.id)
            .values(is_primary=False)
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resume, field, value)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/{resume_id}/status", response_model=ResumeStatusResponse)
def get_resume_status(resume_id: int, current_user: CurrentUser, db: DbSession) -> Resume:
    return _get_owned_resume_or_404(db, current_user.id, resume_id)


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, current_user: CurrentUser, db: DbSession) -> Resume:
    return _get_owned_resume_or_404(db, current_user.id, resume_id)


@router.post(
    "/{resume_id}/ats-analysis",
    response_model=AtsAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ats_analysis(
    resume_id: int,
    payload: AtsAnalysisRequest,
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
) -> AtsAnalysis:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)

    if resume.parse_status != ParseStatus.COMPLETED or not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV henüz başarıyla ayrıştırılmadı; önce parse işleminin "
            "tamamlanmasını bekleyin.",
        )

    job_posting = None
    if payload.job_posting_id is not None:
        job_posting = db.scalar(
            select(JobPosting).where(
                JobPosting.id == payload.job_posting_id,
                JobPosting.user_id == current_user.id,
            )
        )
        if job_posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı"
            )

    try:
        result = analyze_resume(resume.parsed_json, resume.structure_analysis, job_posting, language=language)
    except AtsAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    analysis = AtsAnalysis(
        resume_id=resume.id,
        job_posting_id=payload.job_posting_id,
        ats_score=result.total_score,
        category_scores=result.category_scores.model_dump(),
        strengths=result.strengths,
        gaps=[gap.model_dump() for gap in result.gaps],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _get_source_content(db: DbSession, resume: Resume) -> dict:
    """Yeniden yazım için kaynak: en güncel versiyonun içeriği, yoksa parsed_json."""
    latest = db.scalar(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id, ResumeVersion.content.is_not(None))
        .order_by(ResumeVersion.version_number.desc())
        .limit(1)
    )
    if latest is not None and latest.content:
        return latest.content
    if resume.parsed_json:
        return resume.parsed_json
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="CV henüz başarıyla ayrıştırılmadı; önce parse işleminin "
        "tamamlanmasını bekleyin.",
    )


@router.post(
    "/{resume_id}/rewrite",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def rewrite(
    resume_id: int,
    payload: RewriteRequest,
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
) -> ResumeVersion:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    source_content = _get_source_content(db, resume)

    job_posting = None
    if payload.edit_level == EditLevel.TARGETED:
        if payload.target_job_posting_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'targeted' düzenleme için target_job_posting_id zorunludur.",
            )
        job_posting = db.scalar(
            select(JobPosting).where(
                JobPosting.id == payload.target_job_posting_id,
                JobPosting.user_id == current_user.id,
            )
        )
        if job_posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı"
            )

    profile = None
    if payload.edit_level == EditLevel.FROM_SCRATCH:
        profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))

    try:
        result = rewrite_resume(
            payload.edit_level, source_content, profile=profile, job_posting=job_posting, language=language
        )
    except CvRewriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    next_number = (
        db.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == resume.id
            )
        )
        or 0
    ) + 1

    version = ResumeVersion(
        resume_id=resume.id,
        job_posting_id=payload.target_job_posting_id,
        version_number=next_number,
        edit_level=payload.edit_level,
        content=result.updated_content.model_dump(),
        change_log=[entry.model_dump() for entry in result.change_log],
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/{resume_id}/versions", response_model=list[ResumeVersionResponse])
def list_versions(
    resume_id: int, current_user: CurrentUser, db: DbSession
) -> list[ResumeVersion]:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    return list(
        db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume.id)
            .order_by(ResumeVersion.version_number.desc())
        )
    )


@router.patch(
    "/{resume_id}/versions/{version_id}", response_model=ResumeVersionResponse
)
def update_version(
    resume_id: int,
    version_id: int,
    payload: ResumeVersionUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ResumeVersion:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    version = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id, ResumeVersion.resume_id == resume.id
        )
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Versiyon bulunamadı"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(version, field, value)
    db.commit()
    db.refresh(version)
    return version


def _active_share(db: DbSession, resume_id: int) -> ResumeShare | None:
    return db.scalar(
        select(ResumeShare)
        .where(ResumeShare.resume_id == resume_id, ResumeShare.revoked_at.is_(None))
        .order_by(desc(ResumeShare.created_at))
        .limit(1)
    )


@router.get("/{resume_id}/share", response_model=ResumeShareResponse | None)
def get_resume_share(resume_id: int, current_user: CurrentUser, db: DbSession):
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    share = _active_share(db, resume.id)
    if share is None:
        return None
    return ResumeShareResponse(token=share.token, revoked=False, created_at=share.created_at)


@router.post(
    "/{resume_id}/share", response_model=ResumeShareResponse, status_code=status.HTTP_201_CREATED
)
def create_resume_share(
    resume_id: int, current_user: CurrentUser, db: DbSession
) -> ResumeShareResponse:
    """Mentor/koç gibi biriyle paylaşılacak, girişsiz salt-okunur bir link üretir.

    Aynı CV için zaten iptal edilmemiş bir link varsa, yenisini üretmek yerine
    onu döner (link, kullanıcı arayüzde tek bir 'aktif link' olarak gösterilir).
    """
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)

    existing = _active_share(db, resume.id)
    if existing is not None:
        return ResumeShareResponse(token=existing.token, revoked=False, created_at=existing.created_at)

    share = ResumeShare(resume_id=resume.id, token=secrets.token_urlsafe(SHARE_TOKEN_BYTES))
    db.add(share)
    db.commit()
    db.refresh(share)
    return ResumeShareResponse(token=share.token, revoked=False, created_at=share.created_at)


@router.delete("/{resume_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_resume_share(resume_id: int, current_user: CurrentUser, db: DbSession) -> None:
    resume = _get_owned_resume_or_404(db, current_user.id, resume_id)
    share = _active_share(db, resume.id)
    if share is not None:
        share.revoked_at = datetime.now(timezone.utc)
        db.commit()
