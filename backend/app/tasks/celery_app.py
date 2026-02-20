from celery import Celery
from app.core.config import settings

celery = Celery(
    "ai_test_copilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

from app.tasks import ingest_tasks, plan_tasks