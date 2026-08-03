from pydantic import BaseModel

from app.models.user import VoiceGender


class UserSettingsUpdate(BaseModel):
    preferred_voice_gender: VoiceGender


class UserSettingsResponse(BaseModel):
    user_id: str
    preferred_voice_gender: VoiceGender
