import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.api.conversation as conversation_api
from app.core.database import get_db
from app.main import app, fastapi_app
from app.schemas.conversation import ConversationMessageRequest
from app.services.conversation.language import detect_language
from app.services.conversation.llm_client import (
    LLMClient,
    LLMConfigurationError,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Hello, could you help me plan my day?", "en"),
        ("Apa khabar, boleh tolong saya hari ini?", "ms"),
        ("你好，今天可以帮我吗？", "zh"),
        ("今日は何をすればいいですか？", "ja"),
    ],
)
def test_detect_language(message: str, expected: str) -> None:
    assert detect_language(message) == expected


@pytest.mark.asyncio
async def test_mock_reply_is_personalized_and_emotion_aware() -> None:
    client = LLMClient(api_key=None, mock_mode=True)

    reply = await client.generate_reply(
        user_name="Ada",
        detected_language="en",
        detected_emotion="sad",
        is_live=True,
        messages=[{"role": "user", "content": "I have had a difficult day."}],
        should_greet=True,
    )

    assert "Good to see you again, Ada" in reply
    assert "one step at a time" in reply


@pytest.mark.asyncio
async def test_mock_reply_uses_detected_language() -> None:
    client = LLMClient(api_key=None, mock_mode=True)

    reply = await client.generate_reply(
        user_name="Mei",
        detected_language="zh",
        detected_emotion="happy",
        is_live=True,
        messages=[{"role": "user", "content": "你好"}],
        should_greet=True,
    )

    assert "Mei" in reply
    assert "再次见到你" in reply


@pytest.mark.asyncio
async def test_live_client_requires_an_api_key() -> None:
    client = LLMClient(api_key=None, mock_mode=False)

    with pytest.raises(LLMConfigurationError):
        await client.generate_reply(
            user_name="Ada",
            detected_language="en",
            detected_emotion=None,
            is_live=True,
            messages=[{"role": "user", "content": "Hello"}],
            should_greet=True,
        )


def test_conversation_accepts_text_or_audio_transcript() -> None:
    text_request = ConversationMessageRequest(
        user_id="user-id",
        message="Hello",
    )
    voice_request = ConversationMessageRequest(
        user_id="user-id",
        audio_transcript_of="你好",
    )

    assert text_request.content == "Hello"
    assert text_request.input_mode == "text"
    assert voice_request.content == "你好"
    assert voice_request.input_mode == "voice"


@pytest.mark.parametrize(
    "payload",
    [
        {"user_id": "user-id"},
        {
            "user_id": "user-id",
            "message": "Hello",
            "audio_transcript_of": "Hello",
        },
    ],
)
def test_conversation_requires_exactly_one_input(
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        ConversationMessageRequest.model_validate(payload)


def test_history_uses_keyword_user_id_and_returns_cors_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeUser:
        id = "test-user"
        name = "Test User"

    async def override_db():
        yield object()

    async def fake_verified_context(*_args, **_kwargs) -> object:
        return object()

    async def fake_get_user_history(
        _db: object,
        *,
        user_id: str,
    ) -> tuple[FakeUser, list[object]]:
        assert user_id == "test-user"
        return FakeUser(), []

    monkeypatch.setattr(
        conversation_api,
        "_get_verified_context",
        fake_verified_context,
    )
    monkeypatch.setattr(
        conversation_api,
        "get_user_history",
        fake_get_user_history,
    )
    fastapi_app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            preflight = client.options(
                "/conversation/users/test-user/history",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            response = client.get(
                "/conversation/users/test-user/history",
                headers={"Origin": "http://localhost:5173"},
            )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert preflight.status_code == 200
    assert "GET" in preflight.headers["access-control-allow-methods"]
    assert preflight.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {
        "user_id": "test-user",
        "user_name": "Test User",
        "messages": [],
        "count": 0,
    }


def test_unhandled_history_errors_keep_cors_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def override_db():
        yield object()

    async def fail_history(*_args, **_kwargs) -> object:
        raise RuntimeError("Unexpected history failure")

    monkeypatch.setattr(
        conversation_api,
        "_get_verified_context",
        fail_history,
    )
    fastapi_app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/conversation/users/test-user/history",
                headers={"Origin": "http://localhost:5173"},
            )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
