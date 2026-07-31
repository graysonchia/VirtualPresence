from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api.voice as voice_api
import app.services.voice.tts as tts_module
from app.main import app
from app.services.voice.stt import (
    SpeechToTextService,
    TranscriptionResult,
)
from app.services.voice.tts import TextToSpeechService


@pytest.mark.asyncio
async def test_stt_uses_a_temporary_audio_file(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = SpeechToTextService()
    captured_path: Path | None = None

    def fake_transcribe(audio_path: Path) -> TranscriptionResult:
        nonlocal captured_path
        captured_path = audio_path
        assert audio_path.exists()
        return TranscriptionResult(
            text="Hello",
            language="en",
            language_probability=0.95,
        )

    monkeypatch.setattr(service, "_transcribe_file", fake_transcribe)
    monkeypatch.setattr(service, "_audio_duration_seconds", lambda _: 1.25)
    caplog.set_level("INFO", logger="uvicorn.error")
    result = await service.transcribe(b"audio-data", suffix=".webm")

    assert result.text == "Hello"
    assert captured_path is not None
    assert not captured_path.exists()
    assert (
        "size_bytes=10 duration_seconds=1.250 suffix=.webm"
        in caplog.messages[0]
    )


def test_tts_selects_language_specific_voices() -> None:
    service = TextToSpeechService(
        default_voice="default",
        mandarin_voice="mandarin",
    )

    assert service.voice_for_language("en-US") == "default"
    assert service.voice_for_language("zh-CN") == "mandarin"
    assert service.voice_for_language("unknown") == "default"


@pytest.mark.asyncio
async def test_tts_collects_mp3_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            assert text == "Hello"
            assert voice == "en-US-AriaNeural"

        async def stream(self):
            yield {"type": "audio", "data": b"first"}
            yield {"type": "WordBoundary", "offset": 0}
            yield {"type": "audio", "data": b"second"}

    monkeypatch.setattr(tts_module.edge_tts, "Communicate", FakeCommunicate)

    audio = await TextToSpeechService().synthesize("Hello", language="en")

    assert audio == b"firstsecond"


def test_voice_endpoints_without_loading_external_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStt:
        async def transcribe(
            self,
            audio_bytes: bytes,
            *,
            suffix: str,
        ) -> TranscriptionResult:
            assert audio_bytes == b"recorded-audio"
            assert suffix == ".webm"
            return TranscriptionResult(
                text="Hello there",
                language="en",
                language_probability=0.91,
            )

    class FakeTts:
        def voice_for_language(self, language: str) -> str:
            assert language == "zh"
            return "zh-CN-TestVoice"

        async def synthesize(self, text: str, *, language: str) -> bytes:
            assert text == "你好"
            assert language == "zh"
            return b"mp3-audio"

    monkeypatch.setattr(voice_api, "get_stt_service", lambda: FakeStt())
    monkeypatch.setattr(voice_api, "get_tts_service", lambda: FakeTts())

    with TestClient(app) as client:
        transcription = client.post(
            "/voice/transcribe",
            files={
                "audio": (
                    "recording.webm",
                    b"recorded-audio",
                    "audio/webm;codecs=opus",
                )
            },
        )
        synthesis = client.post(
            "/voice/synthesize",
            json={"text": "你好", "language": "zh"},
        )

    assert transcription.status_code == 200
    assert transcription.json() == {
        "text": "Hello there",
        "detected_language": "en",
        "language_confidence": 0.91,
    }
    assert synthesis.status_code == 200
    assert synthesis.content == b"mp3-audio"
    assert synthesis.headers["content-type"] == "audio/mpeg"
    assert synthesis.headers["x-voice"] == "zh-CN-TestVoice"


def test_voice_validation_logs_missing_multipart_field(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING", logger="uvicorn.error")

    with TestClient(app) as client:
        response = client.post(
            "/voice/transcribe",
            json={},
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == [
        {
            "type": "missing",
            "loc": ["body", "audio"],
            "msg": "Field required",
            "input": None,
        }
    ]
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert any(
        "path=/voice/transcribe" in message
        and "'loc': ('body', 'audio')" in message
        for message in caplog.messages
    )
