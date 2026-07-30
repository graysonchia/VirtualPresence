from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "VirtualPresence API"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"

    database_url: str = (
        "postgresql+asyncpg://postgres:rodolfo@localhost:5432/virtualpresence"
    )
    database_url_sync: str = (
        "postgresql+psycopg://postgres:rodolfo@localhost:5432/virtualpresence"
    )

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    frontend_origins: list[str] = ["http://localhost:5173"]

    face_match_threshold: float = 0.363
    face_detection_threshold: float = 0.9
    liveness_threshold: float = 0.70
    max_upload_bytes: int = 10 * 1024 * 1024
    face_model_dir: Path = BACKEND_DIR / "app" / "services" / "face" / "models"
    enrollment_storage_dir: Path = BACKEND_DIR / "storage" / "enrollments"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
