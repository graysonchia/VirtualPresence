import pytest
from pydantic import ValidationError

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
