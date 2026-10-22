import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.agents.resume_parser import ResumeParseError, parse_resume_text
from app.db.session import SessionLocal
from app.models import Application, ApplicationStatus, ParseStatus, Resume, User
from app.services.email import send_reminder_digest
from app.services.extraction import extract_text
from app.services.storage import get_file_path
from app.services.structure_analysis import analyze_structure
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Görüşme tarihi bu pencere içine giren başvurular için hatırlatma gönderilir.
INTERVIEW_REMINDER_WINDOW = timedelta(hours=48)
# Bu süredir güncellenmemiş, henüz sonuçlanmamış başvurular "durgun" sayılır.
STALE_APPLICATION_THRESHOLD = timedelta(days=14)
# Aynı hatırlatmayı tekrar tekrar göndermemek için minimum bekleme.
REMINDER_COOLDOWN = timedelta(hours=20)

_TERMINAL_STATUSES = {ApplicationStatus.OFFER, ApplicationStatus.REJECTED}


def run_resume_parse(resume_id: int) -> None:
    """CV parse pipeline'ının tamamı: metin çıkar → yapısal analiz → Claude → kaydet.

    Celery task'ından bağımsız çağrılabilir (testlerde senkron kullanılır).
    """
    db = SessionLocal()
    try:
        resume = db.get(Resume, resume_id)
        if resume is None:
            logger.warning("Resume %s bulunamadı, parse atlandı", resume_id)
            return

        resume.parse_status = ParseStatus.PROCESSING
        resume.parse_error = None
        db.commit()

        try:
            with get_file_path(resume.file_path) as local_path:
                extraction = extract_text(local_path, resume.content_type)
                
            resume.raw_text = extraction.text
            resume.page_count = extraction.page_count
            resume.structure_analysis = analyze_structure(extraction)
            db.commit()  # LLM çağrısı başarısız olsa bile çıkarılan metin kaybolmasın

            if not extraction.text.strip():
                raise ResumeParseError("CV'den okunabilir metin çıkarılamadı. Metni seçilebilir bir PDF veya DOCX dosyası yükle.")

            parsed = parse_resume_text(extraction.text)
            resume.parsed_json = parsed.model_dump()
            resume.parse_status = ParseStatus.COMPLETED
            db.commit()
        except Exception as exc:
            logger.exception("Resume %s parse edilemedi", resume_id)
            db.rollback()
            resume.parse_status = ParseStatus.FAILED
            resume.parse_error = (
                str(exc) if isinstance(exc, ResumeParseError)
                else "Görseldeki metin OCR ile okunamadı. Metni seçilebilir PDF veya DOCX yükle."
                if isinstance(exc, ValueError) and "OCR" in str(exc)
                else "CV işlenirken beklenmeyen bir hata oluştu. Lütfen yeniden dene; sorun sürerse site yöneticisine bildir."
            )
            db.commit()
    finally:
        db.close()


@celery_app.task(name="resumes.parse")
def parse_resume_task(resume_id: int) -> None:
    run_resume_parse(resume_id)


def run_reminder_digest() -> int:
    """Her kullanıcı için yaklaşan görüşme + durgun başvuru özetini hazırlar.

    Celery task'ından bağımsız çağrılabilir (testlerde ve manuel tetiklemede
    senkron kullanılır). Kaç kullanıcıya hatırlatma gönderildiğini döner.
    """
    db = SessionLocal()
    sent_count = 0
    try:
        now = datetime.now(timezone.utc)
        users = list(db.scalars(select(User).where(User.is_active.is_(True))))

        for user in users:
            applications = list(
                db.scalars(select(Application).where(Application.user_id == user.id))
            )
            if not applications:
                continue

            upcoming_interviews = []
            stale_applications = []

            for app in applications:
                already_reminded_recently = (
                    app.last_reminded_at is not None
                    and now - app.last_reminded_at < REMINDER_COOLDOWN
                )
                if already_reminded_recently:
                    continue

                reminded = False

                if (
                    app.interview_at is not None
                    and now <= app.interview_at <= now + INTERVIEW_REMINDER_WINDOW
                ):
                    upcoming_interviews.append(
                        {
                            "position": app.position,
                            "company": app.company,
                            "interview_at": app.interview_at.isoformat(),
                        }
                    )
                    reminded = True

                elif (
                    app.status not in _TERMINAL_STATUSES
                    and now - app.updated_at >= STALE_APPLICATION_THRESHOLD
                ):
                    stale_applications.append(
                        {
                            "position": app.position,
                            "company": app.company,
                            "status": app.status.value,
                            "days_since_update": (now - app.updated_at).days,
                        }
                    )
                    reminded = True

                if reminded:
                    app.last_reminded_at = now

            if upcoming_interviews or stale_applications:
                send_reminder_digest(user.email, upcoming_interviews, stale_applications)
                sent_count += 1
                db.commit()

        return sent_count
    finally:
        db.close()


@celery_app.task(name="applications.send_reminder_digest")
def send_reminder_digest_task() -> int:
    return run_reminder_digest()
