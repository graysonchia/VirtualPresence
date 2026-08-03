from pydantic import BaseModel, Field, field_validator


class TranscriptionResponse(BaseModel):
    text: str
    detected_language: str
    language_confidence: float


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2, max_length=16)
    user_id: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Text cannot be empty.")
        return text

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().lower()
