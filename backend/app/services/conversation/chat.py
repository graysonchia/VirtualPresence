from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation_message import ConversationMessage, MessageRole
from app.models.interaction_session import InteractionSession
from app.models.user import User
from app.services.conversation.language import detect_language
from app.services.conversation.llm_client import LLMClient
from app.services.conversation.memory import (
    get_relevant_memory_facts,
    remember_message_facts,
)


class ConversationUserNotFoundError(LookupError):
    pass


class ConversationAccessError(PermissionError):
    pass


@dataclass(slots=True)
class ConversationReply:
    session_id: str
    assistant_message: ConversationMessage
    detected_language: str


async def send_message(
    db: AsyncSession,
    llm_client: LLMClient,
    *,
    user_id: str,
    message_text: str,
    detected_emotion: str | None,
    is_live: bool,
    recognized_at: datetime,
) -> ConversationReply:
    user = await db.get(User, user_id)
    if user is None:
        raise ConversationUserNotFoundError("User not found.")
    if not is_live:
        raise ConversationAccessError(
            "A verified live recognition is required before chatting."
        )

    session = await _get_or_create_session(
        db,
        user_id=user.id,
        detected_emotion=detected_emotion,
        recognized_at=recognized_at,
    )
    session_history = await _session_history(db, session.id)
    history = await _user_message_history(db, user.id)
    relevant_facts = await get_relevant_memory_facts(
        db,
        user_id=user.id,
        message_text=message_text,
    )
    language = detect_language(message_text, fallback=user.preferred_language)
    user_message = ConversationMessage(
        id=str(uuid4()),
        session_id=session.id,
        role=MessageRole.USER,
        content=message_text.strip(),
    )
    db.add(user_message)

    llm_messages = [
        {"role": item.role.value, "content": item.content}
        for item in history[-settings.conversation_context_messages :]
    ]
    llm_messages.append({"role": "user", "content": user_message.content})
    should_greet = not any(
        item.role == MessageRole.ASSISTANT for item in session_history
    )
    try:
        reply_text = await llm_client.generate_reply(
            user_name=user.name,
            detected_language=language,
            detected_emotion=detected_emotion,
            is_live=is_live,
            messages=llm_messages,
            should_greet=should_greet,
            memory_facts=[fact.fact_text for fact in relevant_facts],
        )
        assistant_message = ConversationMessage(
            id=str(uuid4()),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=reply_text,
        )
        db.add(assistant_message)
        await remember_message_facts(
            db,
            user_id=user.id,
            message_text=user_message.content,
        )
        await db.commit()
        await db.refresh(assistant_message)
    except Exception:
        await db.rollback()
        raise

    return ConversationReply(
        session_id=session.id,
        assistant_message=assistant_message,
        detected_language=language,
    )


async def get_user_history(
    db: AsyncSession,
    *,
    user_id: str,
) -> tuple[User, list[ConversationMessage]]:
    user = await db.get(User, user_id)
    if user is None:
        raise ConversationUserNotFoundError("User not found.")
    return user, await _user_message_history(db, user_id)


async def _get_or_create_session(
    db: AsyncSession,
    *,
    user_id: str,
    detected_emotion: str | None,
    recognized_at: datetime,
) -> InteractionSession:
    result = await db.execute(
        select(InteractionSession)
        .where(
            InteractionSession.user_id == user_id,
            InteractionSession.ended_at.is_(None),
        )
        .order_by(InteractionSession.started_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session is not None and session.started_at < recognized_at:
        session.ended_at = datetime.now(timezone.utc)
        session = None

    if session is None:
        session = InteractionSession(
            id=str(uuid4()),
            user_id=user_id,
            detected_emotion_summary=detected_emotion,
        )
        db.add(session)
        await db.flush()
    elif detected_emotion:
        session.detected_emotion_summary = detected_emotion
    return session


async def _session_history(
    db: AsyncSession,
    session_id: str,
) -> list[ConversationMessage]:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.timestamp, ConversationMessage.id)
    )
    return list(result.scalars().all())


async def _user_message_history(
    db: AsyncSession,
    user_id: str,
) -> list[ConversationMessage]:
    result = await db.execute(
        select(ConversationMessage)
        .join(
            InteractionSession,
            ConversationMessage.session_id == InteractionSession.id,
        )
        .where(InteractionSession.user_id == user_id)
        .order_by(ConversationMessage.timestamp, ConversationMessage.id)
    )
    return list(result.scalars().all())
