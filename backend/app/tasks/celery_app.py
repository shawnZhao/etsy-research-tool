from celery import Celery
from app.config import settings

celery_app = Celery(
    "etsy_research",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.keyword_tasks",
        "app.tasks.sync_tasks",
        "app.tasks.seo_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_expires=3600,
)
