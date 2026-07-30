from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "virtualpresence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.services.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kuala_Lumpur",
    enable_utc=True,
)

