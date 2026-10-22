from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.agents.career_coach import CareerCoachError, build_roadmap
from app.api.deps import CurrentUser, DbSession, Language
from app.models import CareerRoadmap, JobPosting, Profile, Resume, ResumeVersion
from app.schemas.roadmap import CareerRoadmapResponse, RoadmapProgressUpdate

router = APIRouter(prefix="/career-roadmap", tags=["career-roadmap"])


def _resolve_resume_content(
    db: DbSession,
    user_id: int,
    resume_version_id: int | None,
    resume_id: int | None,
) -> tuple[dict, Resume | None, ResumeVersion | None]:
    if resume_version_id is not None:
        version = db.scalar(
            select(ResumeVersion)
            .join(Resume, Resume.id == ResumeVersion.resume_id)
            .where(ResumeVersion.id == resume_version_id, Resume.user_id == user_id)
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV versiyonu bulunamadı"
            )
        resume = db.get(Resume, version.resume_id)
        content = version.content
    elif resume_id is not None:
        resume = db.scalar(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı"
            )
        version = None
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
    return content, resume, version


@router.get("", response_model=CareerRoadmapResponse)
def get_career_roadmap(
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
    target_role: str = Query(min_length=2, max_length=255),
    resume_version_id: int | None = Query(default=None),
    resume_id: int | None = Query(default=None),
    job_posting_id: int | None = Query(default=None),
    refresh: bool = Query(
        default=False, description="true ise kayıtlı yol haritasını yok sayıp yeniden üretir"
    ),
) -> CareerRoadmap:
    content, resume, version = _resolve_resume_content(
        db, current_user.id, resume_version_id, resume_id
    )

    job_posting = None
    if job_posting_id is not None:
        job_posting = db.scalar(
            select(JobPosting).where(
                JobPosting.id == job_posting_id, JobPosting.user_id == current_user.id
            )
        )
        if job_posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı"
            )

    # GET idempotent kalsın: aynı girdi kombinasyonu için kayıtlı harita varsa
    # (ve ilerleme işaretlenmiş olabilir) onu dön; refresh=true ile yeniden üret.
    existing = db.scalar(
        select(CareerRoadmap).where(
            CareerRoadmap.user_id == current_user.id,
            CareerRoadmap.target_role == target_role,
            CareerRoadmap.resume_version_id == (version.id if version else None),
            CareerRoadmap.resume_id == (resume.id if resume else None),
            CareerRoadmap.job_posting_id == job_posting_id,
        )
    )
    if existing is not None and not refresh:
        return existing

    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))

    try:
        result = build_roadmap(
            content,
            target_role,
            job_requirements=job_posting.requirements if job_posting else None,
            job_description=job_posting.description if job_posting else None,
            profile_goal=profile.career_goal if profile else None,
            language=language,
        )
    except CareerCoachError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    roadmap = existing or CareerRoadmap(
        user_id=current_user.id,
        resume_id=resume.id if resume else None,
        resume_version_id=version.id if version else None,
        job_posting_id=job_posting_id,
        target_role=target_role,
        completed_steps=[],
    )
    roadmap.current_strengths = result.current_strengths
    roadmap.gaps = result.gaps
    roadmap.development_plan = [step.model_dump() for step in result.development_plan]
    if existing is not None:
        # Yeniden üretimde plan değişti; artık geçersiz adım işaretlerini temizle
        valid = {step.step for step in result.development_plan}
        roadmap.completed_steps = [s for s in (roadmap.completed_steps or []) if s in valid]

    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap


@router.get("/{roadmap_id}", response_model=CareerRoadmapResponse)
def get_roadmap_by_id(
    roadmap_id: int, current_user: CurrentUser, db: DbSession
) -> CareerRoadmap:
    return _get_owned_roadmap_or_404(db, current_user.id, roadmap_id)


@router.patch("/{roadmap_id}/progress", response_model=CareerRoadmapResponse)
def update_progress(
    roadmap_id: int,
    payload: RoadmapProgressUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> CareerRoadmap:
    roadmap = _get_owned_roadmap_or_404(db, current_user.id, roadmap_id)

    valid_steps = {
        step.get("step") for step in (roadmap.development_plan or []) if isinstance(step, dict)
    }
    unknown = sorted(set(payload.completed_steps) - valid_steps)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Yol haritasında bulunmayan adım numaraları: {unknown}",
        )

    roadmap.completed_steps = sorted(set(payload.completed_steps))
    db.commit()
    db.refresh(roadmap)
    return roadmap


def _get_owned_roadmap_or_404(
    db: DbSession, user_id: int, roadmap_id: int
) -> CareerRoadmap:
    roadmap = db.scalar(
        select(CareerRoadmap).where(
            CareerRoadmap.id == roadmap_id, CareerRoadmap.user_id == user_id
        )
    )
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Yol haritası bulunamadı"
        )
    return roadmap
