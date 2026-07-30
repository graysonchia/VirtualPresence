from datetime import datetime, timezone

from app.services.celery_app import celery_app


@celery_app.task(name="virtualpresence.health_check")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
