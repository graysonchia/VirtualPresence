from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.recognition_event import RecognitionEvent, RecognitionOutcome
from app.schemas.conversation import (
    ConversationHistoryItem,
    ConversationHistoryResponse,
    ConversationMessageRequest,
    ConversationMessageResponse,
)
from app.services.conversation import (
    ConversationAccessError,
    ConversationUserNotFoundError,
    get_llm_client,
    send_message,
)
from app.services.conversation.chat import get_user_history
from app.services.conversation.llm_client import (
    LLMConfigurationError,
    LLMServiceError,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])


async def _get_verified_context(
    db: AsyncSession,
    user_id: str,
) -> RecognitionEvent:
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.conversation_recognition_ttl_seconds
    )
    result = await db.execute(
        select(RecognitionEvent)
        .where(
            RecognitionEvent.user_id == user_id,
            RecognitionEvent.is_live.is_(True),
            RecognitionEvent.outcome == RecognitionOutcome.RECOGNIZED,
            RecognitionEvent.timestamp >= cutoff,
        )
        .order_by(RecognitionEvent.timestamp.desc())
        .limit(1)
    )
    recognition = result.scalar_one_or_none()
    if recognition is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "A recent successful live face recognition is required before "
                "using this conversation."
            ),
        )
    return recognition


@router.post(
    "/message",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    payload: ConversationMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationMessageResponse:
    recognition = await _get_verified_context(db, payload.user_id)

    try:
        result = await send_message(
            db=db,
            llm_client=get_llm_client(),
            user_id=payload.user_id,
            message_text=payload.content,
            detected_emotion=recognition.detected_emotion,
            is_live=recognition.is_live,
            recognized_at=recognition.timestamp,
        )
    except ConversationUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ConversationMessageResponse(
        user_id=payload.user_id,
        session_id=result.session_id,
        assistant_reply=result.assistant_message.content,
        detected_input_language=result.detected_language,
        input_mode=payload.input_mode,
        timestamp=result.assistant_message.timestamp,
    )


@router.get(
    "/users/{user_id}/history",
    response_model=ConversationHistoryResponse,
)
async def read_user_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationHistoryResponse:
    await _get_verified_context(db, user_id)

    try:
        user, messages = await get_user_history(db, user_id=user_id)
    except ConversationUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    history = [ConversationHistoryItem.model_validate(message) for message in messages]
    return ConversationHistoryResponse(
        user_id=user.id,
        user_name=user.name,
        messages=history,
        count=len(history),
    )
