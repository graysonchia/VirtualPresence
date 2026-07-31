import asyncio
import tempfile
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel


class AudioTranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str
    language: str
    language_probability: float


class SpeechToTextService:
    def __init__(
        self,
        *,
        model_size: str = settings.stt_model_size,
        device: str = settings.stt_device,
        compute_type: str = settings.stt_compute_type,
        beam_size: int = settings.stt_beam_size,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self._model: WhisperModel | None = None
        self._inference_lock = threading.Lock()

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        suffix: str,
    ) -> TranscriptionResult:
        if not audio_bytes:
            raise AudioTranscriptionError("The uploaded audio is empty.")

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            ) as temporary_file:
                temporary_file.write(audio_bytes)
                temporary_path = Path(temporary_file.name)

            return await asyncio.to_thread(
                self._transcribe_file,
                temporary_path,
            )
        except AudioTranscriptionError:
            raise
        except Exception as exc:
            raise AudioTranscriptionError(
                "The audio could not be transcribed."
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _transcribe_file(self, audio_path: Path) -> TranscriptionResult:
        with self._inference_lock:
            model = self._get_model()
            segments, info = model.transcribe(
                str(audio_path),
                beam_size=self.beam_size,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()

        if not text:
            raise AudioTranscriptionError(
                "No speech was detected in the uploaded audio."
            )
        return TranscriptionResult(
            text=text,
            language=info.language or "en",
            language_probability=float(info.language_probability or 0.0),
        )

    def _get_model(self) -> "WhisperModel":
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model


@lru_cache(maxsize=1)
def get_stt_service() -> SpeechToTextService:
    return SpeechToTextService()
