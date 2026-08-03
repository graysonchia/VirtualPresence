from datetime import date

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    total_users: int = 0
    total_sessions: int = 0
    total_messages: int = 0
    total_recognition_attempts: int = 0
    average_session_length_seconds: float = 0.0
    average_messages_per_session: float = 0.0
    recognition_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    liveness_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    liveness_fail_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    spoof_detection_count: int = 0
    total_memory_facts: int = 0
    referenced_memory_facts: int = 0
    average_referenced_facts_per_session: float = 0.0


class RecognitionTrendPoint(BaseModel):
    date: date
    total_attempts: int = 0
    recognized_count: int = 0
    spoof_detection_count: int = 0
    average_match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    liveness_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    liveness_fail_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    low_confidence_count: int = 0
    medium_confidence_count: int = 0
    high_confidence_count: int = 0


class RecognitionTrendsResponse(BaseModel):
    days: int
    start_date: date
    end_date: date
    points: list[RecognitionTrendPoint]


class EmotionDistributionItem(BaseModel):
    emotion: str
    count: int
    percentage: float = Field(ge=0.0, le=1.0)


class EmotionDistributionResponse(BaseModel):
    total_observations: int
    emotions: list[EmotionDistributionItem]


class DailyUsagePoint(BaseModel):
    date: date
    sessions: int = 0
    messages: int = 0
    average_messages_per_session: float = 0.0
    average_session_length_seconds: float = 0.0


class HourlyUsagePoint(BaseModel):
    hour: int = Field(ge=0, le=23)
    sessions: int = 0
    messages: int = 0


class UsagePatternsResponse(BaseModel):
    timezone: str = "UTC"
    total_sessions: int
    total_messages: int
    average_messages_per_session: float
    average_session_length_seconds: float
    most_active_hour: int | None = Field(default=None, ge=0, le=23)
    daily: list[DailyUsagePoint]
    hourly: list[HourlyUsagePoint]
