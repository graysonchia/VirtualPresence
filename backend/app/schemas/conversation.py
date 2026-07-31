from datetime import datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.conversation_message import MessageRole


class ConversationMessageRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    message: str | None = Field(default=None, min_length=1, max_length=4000)
    audio_transcript_of: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
    )

    @field_validator("message", "audio_transcript_of")
    @classmethod
    def strip_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        content = value.strip()
        if not content:
            raise ValueError("Message content cannot be empty.")
        return content

    @model_validator(mode="after")
    def require_one_input(self) -> Self:
        if (self.message is None) == (self.audio_transcript_of is None):
            raise ValueError(
                "Provide exactly one of message or audio_transcript_of."
            )
        return self

    @property
    def content(self) -> str:
        return self.message or self.audio_transcript_of or ""

    @property
    def input_mode(self) -> Literal["text", "voice"]:
        return "voice" if self.audio_transcript_of is not None else "text"


class ConversationMessageResponse(BaseModel):
    user_id: str
    session_id: str
    assistant_reply: str
    detected_input_language: str
    input_mode: Literal["text", "voice"]
    timestamp: datetime


class ConversationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime


class ConversationHistoryResponse(BaseModel):
    user_id: str
    user_name: str
    messages: list[ConversationHistoryItem]
    count: int
