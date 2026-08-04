from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.recognition_event import RecognitionOutcome
from app.models.user import UserStatus, VoiceGender


class EnrolledUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    enrolled_at: datetime
    preferred_language: str
    preferred_voice_gender: VoiceGender
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


class EdgeInferenceProfile(BaseModel):
    model_size_mb: float = Field(ge=0.0)
    mean_latency_ms: float = Field(ge=0.0)
    accuracy_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    model_size_metric: str
    precision: str


class EdgeBenchmarkResponse(BaseModel):
    standard: EdgeInferenceProfile
    edge_optimized: EdgeInferenceProfile
    sample_count: int = Field(ge=0)
    samples_source: str
    size_reduction_percent: float
    latency_reduction_percent: float
    accuracy_delta_percentage_points: float | None = None
    notes: list[str]


class EdgeArchitectureSummary(BaseModel):
    concept: str
    deployment_scope: str
    architecture_pattern: list[str]
    privacy_boundary: list[str]
    performance_tradeoffs: list[str]
    limitations: list[str]
    project_status: str


class UserListResponse(BaseModel):
    users: list[EnrolledUser]
    count: int


class HealthResponse(BaseModel):
    status: str
    service: str
