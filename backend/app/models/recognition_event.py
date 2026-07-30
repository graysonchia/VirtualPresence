import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class RecognitionOutcome(str, enum.Enum):
    RECOGNIZED = "recognized"
    UNRECOGNIZED = "unrecognized"
    SPOOF_DETECTED = "spoof_detected"


class RecognitionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recognition_events"

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected_emotion: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    emotion_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    is_live: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    liveness_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    outcome: Mapped[RecognitionOutcome] = mapped_column(
        Enum(
            RecognitionOutcome,
            name="recognition_outcome",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(back_populates="recognition_events")
