from functools import lru_cache

import edge_tts

from app.core.config import settings


class SpeechSynthesisError(RuntimeError):
    pass


LANGUAGE_VOICES = {
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "id": "id-ID-GadisNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "ms": "ms-MY-YasminNeural",
    "pt": "pt-BR-FranciscaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}


class TextToSpeechService:
    def __init__(
        self,
        *,
        default_voice: str = settings.tts_default_voice,
        mandarin_voice: str = settings.tts_mandarin_voice,
    ) -> None:
        self.default_voice = default_voice
        self.mandarin_voice = mandarin_voice

    def voice_for_language(self, language: str) -> str:
        normalized = language.strip().lower().split("-", maxsplit=1)[0]
        if normalized == "zh":
            return self.mandarin_voice
        if normalized == "en":
            return self.default_voice
        return LANGUAGE_VOICES.get(normalized, self.default_voice)

    async def synthesize(self, text: str, *, language: str) -> bytes:
        normalized_text = text.strip()
        if not normalized_text:
            raise SpeechSynthesisError("Text is required for speech synthesis.")

        try:
            communicator = edge_tts.Communicate(
                normalized_text,
                self.voice_for_language(language),
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
            raise SpeechSynthesisError(
                "The speech service returned no audio."
            )
        return b"".join(chunks)


@lru_cache(maxsize=1)
def get_tts_service() -> TextToSpeechService:
    return TextToSpeechService()
