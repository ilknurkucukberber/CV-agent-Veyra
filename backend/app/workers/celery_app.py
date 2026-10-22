from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "cv_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "daily-reminder-digest": {
            "task": "applications.send_reminder_digest",
            # Her gün 08:00 UTC'de: yaklaşan görüşmeler + durgun başvurular.
            "schedule": crontab(hour=8, minute=0),
        },
    },
)

# Görev modülleri tanımlandıkça buraya eklenecek:
# celery_app.autodiscover_tasks(["app.workers"])
