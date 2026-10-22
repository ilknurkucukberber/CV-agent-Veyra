from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select

from app.api.deps import DbSession
from app.models import AtsAnalysis, Resume, ResumeShare
from app.schemas.resume import PublicResumeShareView

router = APIRouter(prefix="/share", tags=["public-share"])


@router.get("/resumes/{token}", response_model=PublicResumeShareView)
def get_shared_resume(token: str, db: DbSession) -> PublicResumeShareView:
    """Girişsiz, salt-okunur CV + en güncel ATS analizi görünümü.

    Yalnızca `create_resume_share` ile üretilmiş, iptal edilmemiş bir token
    kabul edilir. Kimlik doğrulaması YOKTUR — token'ın kendisi erişim
    kanıtıdır (bir mentor/koç ile paylaşılan link mantığı).
    """
    share = db.scalar(select(ResumeShare).where(ResumeShare.token == token))
    if share is None or share.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu paylaşım linki geçersiz veya iptal edilmiş.",
        )

    resume = db.get(Resume, share.resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı")

    latest_analysis = db.scalar(
        select(AtsAnalysis)
        .where(AtsAnalysis.resume_id == resume.id)
        .order_by(desc(AtsAnalysis.created_at))
        .limit(1)
    )

    return PublicResumeShareView(
        resume_title=resume.title,
        parsed_json=resume.parsed_json,
        latest_ats_analysis=latest_analysis,
        shared_at=share.created_at,
    )
