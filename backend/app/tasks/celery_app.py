from celery import Celery
from app.config import settings

celery_app = Celery(
    "etsy_research",
    broker=settings.redis_url,
    backend=settings.redis_url,
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
)
