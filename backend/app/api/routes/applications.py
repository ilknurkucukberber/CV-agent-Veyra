from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, Language
from app.core.pagination import Offset, OptionalLimit, paginate
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import JobPosting
from app.models.resume import ResumeVersion
from app.schemas.application import (
    ApplicationCreate,
    ApplicationFunnel,
    ApplicationResponse,
    ApplicationUpdate,
    FunnelConversion,
    FunnelStage,
)
from app.agents.interview_schema import SessionType
from app.agents.interview_agent import generate_questions
from app.workers.tasks import run_reminder_digest

router = APIRouter(prefix="/applications", tags=["applications"])

# Doğrusal huni sırası. AWAITING_RESPONSE ve REJECTED bu sıranın dışında
# tutulur çünkü hangi aşamada olduklarını/hangi aşamadan koptuklarını
# durum alanından kesin olarak bilemeyiz (bkz. ApplicationFunnel.note).
FUNNEL_STAGE_ORDER = [
    (ApplicationStatus.SAVED, "Kaydedildi"),
    (ApplicationStatus.APPLIED, "Başvuruldu"),
    (ApplicationStatus.HR_INTERVIEW, "İK Görüşmesi"),
    (ApplicationStatus.TECHNICAL_INTERVIEW, "Teknik Görüşme"),
    (ApplicationStatus.OFFER, "Teklif"),
]


@router.get("", response_model=list[ApplicationResponse])
def get_applications(
    current_user: CurrentUser, db: DbSession, limit: OptionalLimit = None, offset: Offset = 0
) -> Any:
    """
    Kullanıcının başvurularını listeler.
    """
    stmt = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    return list(db.scalars(paginate(stmt, limit, offset)).all())


@router.post("/analytics/trigger-reminder-digest")
def trigger_reminder_digest(current_user: CurrentUser) -> Any:
    """Hatırlatma özetini (yaklaşan görüşmeler + durgun başvurular) hemen çalıştırır.

    Normalde her gün 08:00 UTC'de Celery beat tarafından tetiklenir; bu uç,
    zamanlamayı beklemeden test/demo amaçlı manuel tetikleme sağlar. Tüm aktif
    kullanıcılar için çalışır (beat'in yapacağıyla aynı davranış).
    """
    notified = run_reminder_digest()
    return {"users_notified": notified}


@router.get("/analytics/funnel", response_model=ApplicationFunnel)
def get_application_funnel(current_user: CurrentUser, db: DbSession) -> Any:
    """
    Başvuru huni analitiği: her aşamaya ULAŞAN (o aşamada veya ötesinde olan)
    başvuru sayısı ve ardışık aşamalar arası dönüşüm oranı.
    """
    stmt = select(Application.status).where(Application.user_id == current_user.id)
    all_statuses = list(db.scalars(stmt).all())

    stage_index = {status: i for i, (status, _label) in enumerate(FUNNEL_STAGE_ORDER)}
    # awaiting_response fiilen "başvuruldu ve yanıt bekleniyor" demektir; en az
    # APPLIED aşamasına ulaşmış sayılır.
    effective_index = {
        status: stage_index[status]
        for status in stage_index
    }
    reached_counts = [0] * len(FUNNEL_STAGE_ORDER)
    rejected_count = 0

    for status in all_statuses:
        if status == ApplicationStatus.REJECTED:
            rejected_count += 1
            continue
        idx = effective_index.get(status)
        if idx is None and status == ApplicationStatus.AWAITING_RESPONSE:
            idx = stage_index[ApplicationStatus.APPLIED]
        if idx is None:
            continue
        for i in range(idx + 1):
            reached_counts[i] += 1

    stages = [
        FunnelStage(key=status.value, label=label, count=reached_counts[i])
        for i, (status, label) in enumerate(FUNNEL_STAGE_ORDER)
    ]

    conversions = []
    for i in range(len(FUNNEL_STAGE_ORDER) - 1):
        from_count = reached_counts[i]
        to_count = reached_counts[i + 1]
        rate = round(to_count / from_count, 4) if from_count > 0 else None
        conversions.append(
            FunnelConversion(
                from_key=FUNNEL_STAGE_ORDER[i][0].value,
                to_key=FUNNEL_STAGE_ORDER[i + 1][0].value,
                from_label=FUNNEL_STAGE_ORDER[i][1],
                to_label=FUNNEL_STAGE_ORDER[i + 1][1],
                rate=rate,
            )
        )

    return ApplicationFunnel(
        stages=stages,
        conversions=conversions,
        rejected_count=rejected_count,
        total_count=len(all_statuses),
    )


@router.post("", response_model=ApplicationResponse)
def create_application(
    application_in: ApplicationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Any:
    """
    Yeni başvuru oluşturur.
    """
    application = Application(
        **application_in.model_dump(),
        user_id=current_user.id,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{id}", response_model=ApplicationResponse)
def get_application(id: int, current_user: CurrentUser, db: DbSession) -> Any:
    """
    Başvuru detayını getirir.
    """
    stmt = select(Application).where(
        Application.id == id, Application.user_id == current_user.id
    )
    application = db.scalars(stmt).first()

    if not application:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    return application


@router.patch("/{id}", response_model=ApplicationResponse)
def update_application(
    id: int,
    application_in: ApplicationUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Any:
    """
    Başvuruyu günceller.
    """
    stmt = select(Application).where(
        Application.id == id, Application.user_id == current_user.id
    )
    application = db.scalars(stmt).first()

    if not application:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    update_data = application_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)

    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{id}")
def delete_application(id: int, current_user: CurrentUser, db: DbSession) -> Any:
    """
    Başvuruyu siler.
    """
    stmt = select(Application).where(
        Application.id == id, Application.user_id == current_user.id
    )
    application = db.scalars(stmt).first()

    if not application:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    db.delete(application)
    db.commit()
    return {"message": "Başvuru başarıyla silindi"}


@router.get("/{id}/prep-checklist")
def get_prep_checklist(id: int, current_user: CurrentUser, db: DbSession, language: Language) -> Any:
    """
    Bu başvuru için mülakat öncesi hazırlık soruları üretir.
    """
    stmt = select(Application).where(
        Application.id == id, Application.user_id == current_user.id
    )
    application = db.scalars(stmt).first()

    if not application:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    if not application.resume_version_id:
        raise HTTPException(
            status_code=400,
            detail="Hazırlık listesi oluşturabilmek için bir CV sürümü seçilmiş olmalıdır.",
        )

    # Get resume content
    stmt = select(ResumeVersion).where(ResumeVersion.id == application.resume_version_id)
    resume_version = db.scalars(stmt).first()

    if not resume_version or not resume_version.content:
        raise HTTPException(status_code=400, detail="CV içeriği bulunamadı.")

    # Get job requirements if linked
    job_title = application.position
    job_requirements = None

    if application.job_posting_id:
        stmt = select(JobPosting).where(JobPosting.id == application.job_posting_id)
        job_posting = db.scalars(stmt).first()
        if job_posting:
            job_requirements = job_posting.requirements

    # Generate questions (using HR for a general mix, or a mix of types)
    try:
        # We can generate technical questions if it's more relevant, or HR.
        # Generating technical questions covers both cv_specific and job_specific effectively.
        result = generate_questions(
            session_type=SessionType.TECHNICAL,
            resume_content=resume_version.content,
            job_title=job_title,
            job_requirements=job_requirements,
            language=language,
        )

        # Add HR questions as well for a comprehensive checklist
        hr_result = generate_questions(
            session_type=SessionType.HR,
            resume_content=resume_version.content,
            job_title=job_title,
            job_requirements=job_requirements,
            language=language,
        )

        all_questions = hr_result.questions + result.questions
        return {"questions": [q.model_dump() for q in all_questions]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
