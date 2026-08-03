from functools import lru_cache

import edge_tts

from app.core.config import settings
from app.models.user import VoiceGender


class SpeechSynthesisError(RuntimeError):
    pass


LANGUAGE_VOICES: dict[str, dict[VoiceGender, str]] = {
    "de": {
        VoiceGender.MALE: "de-DE-ConradNeural",
        VoiceGender.FEMALE: "de-DE-KatjaNeural",
    },
    "es": {
        VoiceGender.MALE: "es-ES-AlvaroNeural",
        VoiceGender.FEMALE: "es-ES-ElviraNeural",
    },
    "fr": {
        VoiceGender.MALE: "fr-FR-HenriNeural",
        VoiceGender.FEMALE: "fr-FR-DeniseNeural",
    },
    "id": {
        VoiceGender.MALE: "id-ID-ArdiNeural",
        VoiceGender.FEMALE: "id-ID-GadisNeural",
    },
    "ja": {
        VoiceGender.MALE: "ja-JP-KeitaNeural",
        VoiceGender.FEMALE: "ja-JP-NanamiNeural",
    },
    "ko": {
        VoiceGender.MALE: "ko-KR-InJoonNeural",
        VoiceGender.FEMALE: "ko-KR-SunHiNeural",
    },
    "ms": {
        VoiceGender.MALE: "ms-MY-OsmanNeural",
        VoiceGender.FEMALE: "ms-MY-YasminNeural",
    },
    "pt": {
        VoiceGender.MALE: "pt-BR-AntonioNeural",
        VoiceGender.FEMALE: "pt-BR-FranciscaNeural",
    },
}


class TextToSpeechService:
    def __init__(
        self,
        *,
        english_male_voice: str = settings.tts_english_male_voice,
        english_female_voice: str = settings.tts_english_female_voice,
        mandarin_male_voice: str = settings.tts_mandarin_male_voice,
        mandarin_female_voice: str = settings.tts_mandarin_female_voice,
        default_voice: str | None = None,
        mandarin_voice: str | None = None,
    ) -> None:
        # Keep the phase-3 constructor names as aliases for callers that
        # customized the former single (female) voice configuration.
        english_male_voice = default_voice or english_male_voice
        mandarin_male_voice = mandarin_voice or mandarin_male_voice
        self.voices = {
            **LANGUAGE_VOICES,
            "en": {
                VoiceGender.MALE: english_male_voice,
                VoiceGender.FEMALE: english_female_voice,
            },
            "zh": {
                VoiceGender.MALE: mandarin_male_voice,
                VoiceGender.FEMALE: mandarin_female_voice,
            },
        }

    def voice_for_language(
        self,
        language: str,
        gender: VoiceGender = VoiceGender.MALE,
    ) -> str:
        normalized = language.strip().lower().split("-", maxsplit=1)[0]
        language_voices = self.voices.get(normalized, self.voices["en"])
        return language_voices[gender]

    async def synthesize(
        self,
        text: str,
        *,
        language: str,
        gender: VoiceGender = VoiceGender.MALE,
    ) -> bytes:
        normalized_text = text.strip()
        if not normalized_text:
            raise SpeechSynthesisError("Text is required for speech synthesis.")

        try:
            communicator = edge_tts.Communicate(
                normalized_text,
                self.voice_for_language(language, gender),
            )
            chunks = [
                message["data"]
                async for message in communicator.stream()
                if message["type"] == "audio"
            ]
        except Exception as exc:
            raise SpeechSynthesisError(
                "Speech synthesis is temporarily unavailable."
            ) from exc

        if not chunks:
            raise SpeechSynthesisError("The speech service returned no audio.")
        return b"".join(chunks)


@lru_cache(maxsize=1)
def get_tts_service() -> TextToSpeechService:
    return TextToSpeechService()
