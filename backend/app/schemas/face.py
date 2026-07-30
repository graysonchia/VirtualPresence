from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.recognition_event import RecognitionOutcome
from app.models.user import UserStatus


class EnrolledUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    enrolled_at: datetime
    preferred_language: str
    status: UserStatus


class EnrollmentResponse(BaseModel):
    message: str
    user: EnrolledUser
    embedding_id: str


class IdentificationResponse(BaseModel):
    outcome: RecognitionOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    user: EnrolledUser | None = None
    faces_detected: int = Field(ge=0)
    detected_emotion: str | None = None
    emotion_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    emotion_scores: dict[str, float] = Field(default_factory=dict)
    is_live: bool
    liveness_confidence: float = Field(ge=0.0, le=1.0)


class UserListResponse(BaseModel):
    users: list[EnrolledUser]
    count: int


class HealthResponse(BaseModel):
    status: str
    service: str
