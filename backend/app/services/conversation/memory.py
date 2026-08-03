import logging
import re
from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utc_now
from app.models.user_memory_fact import UserMemoryFact


logger = logging.getLogger("uvicorn.error")

MAX_FACT_LENGTH = 500
DEFAULT_RELEVANT_FACT_LIMIT = 5
_SENTENCE_SPLIT = re.compile(r"[.!?\n。！？]+")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_CJK_CHARACTER = re.compile(r"[\u3400-\u9fff]")
_TRANSIENT_STATE = re.compile(
    r"\bi(?:'m| am)\s+(?:sad|happy|angry|tired|hungry|busy|bored|fine|"
    r"okay|ok|sick|afraid|upset|stressed)\b",
    re.IGNORECASE,
)
_CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "project",
        re.compile(
            r"\b(?:i(?:'m| am)\s+(?:working on|building|developing|creating)|"
            r"my\s+(?:school\s+)?project\s+(?:is|involves))\b|"
            r"(?:我正在做|我的项目)|"
            r"\bsaya\s+sedang\s+(?:mengerjakan|membangunkan)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "preference",
        re.compile(
            r"\b(?:i\s+(?:prefer|like|love|enjoy)|my\s+favou?rite\b|"
            r"my\s+preference\s+is)\b|"
            r"(?:我喜欢|我偏好|我最喜欢)|"
            r"\bsaya\s+(?:suka|lebih\s+suka|minat)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "goal",
        re.compile(
            r"\b(?:i\s+(?:want to|plan to|hope to|am learning|am studying)|"
            r"i'm\s+(?:learning|studying)|my\s+goal\s+is)\b|"
            r"(?:我正在学习|我的目标是)|"
            r"\bsaya\s+(?:mahu|ingin|sedang\s+belajar)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "profile",
        re.compile(
            r"\b(?:i\s+(?:work as|study at|live in)|i(?:'m| am)\s+an?\s+"
            r"(?:[\w-]+\s+){0,3}"
            r"(?:student|teacher|developer|designer|engineer|researcher)|"
            r"my\s+(?:name|job|role)\s+is)\b|"
            r"(?:我住在|我就读于|我的工作是)|"
            r"\bsaya\s+(?:tinggal di|belajar di|bekerja sebagai)\b",
            re.IGNORECASE,
        ),
    ),
)
_STOP_WORDS = {
    "a",
    "am",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "please",
    "the",
    "to",
    "what",
    "with",
}


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    fact_text: str
    category: str


def extract_memory_candidates(message_text: str) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    for raw_sentence in _SENTENCE_SPLIT.split(message_text):
        sentence = " ".join(raw_sentence.strip().split())
        if not sentence:
            continue
        if len(sentence.split()) < 3 and not _CJK_CHARACTER.search(sentence):
            logger.info(
                "[memory] extraction decision=ignored reason=too_short sentence=%r",
                sentence,
            )
            continue
        if len(sentence) > MAX_FACT_LENGTH:
            logger.info(
                "[memory] extraction decision=ignored reason=too_long sentence=%r",
                sentence,
            )
            continue
        if _TRANSIENT_STATE.search(sentence):
            logger.info(
                "[memory] extraction decision=ignored reason=transient_state "
                "sentence=%r",
                sentence,
            )
            continue
        for category, pattern in _CATEGORY_PATTERNS:
            if pattern.search(sentence):
                candidates.append(
                    MemoryCandidate(fact_text=sentence, category=category)
                )
                logger.info(
                    "[memory] extraction decision=candidate category=%s sentence=%r",
                    category,
                    sentence,
                )
                break
        else:
            logger.info(
                "[memory] extraction decision=ignored reason=no_pattern sentence=%r",
                sentence,
            )
    return candidates


def normalize_fact_text(text: str) -> str:
    normalized = text.casefold().replace("’", "'")
    normalized = re.sub(r"\bi'm\b", "i am", normalized)
    normalized = normalized.replace("favourite", "favorite")
    return " ".join(_WORD.findall(normalized))


def facts_are_duplicates(left: str, right: str) -> bool:
    left_normalized = normalize_fact_text(left)
    right_normalized = normalize_fact_text(right)
    if left_normalized == right_normalized:
        return True
    left_tokens = _meaningful_tokens(left_normalized)
    right_tokens = _meaningful_tokens(right_normalized)
    if not left_tokens or not right_tokens:
        return False
    similarity = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    return similarity >= 0.85


def rank_relevant_facts(
    facts: list[UserMemoryFact],
    message_text: str,
    *,
    limit: int = DEFAULT_RELEVANT_FACT_LIMIT,
) -> list[UserMemoryFact]:
    query_tokens = _meaningful_tokens(normalize_fact_text(message_text))
    if not query_tokens or limit <= 0:
        return []

    scored: list[tuple[float, datetime, UserMemoryFact]] = []
    for fact in facts:
        fact_tokens = _meaningful_tokens(normalize_fact_text(fact.fact_text))
        overlap = query_tokens & fact_tokens
        if not overlap:
            continue
        score = len(overlap) / sqrt(len(query_tokens) * len(fact_tokens))
        recency = fact.last_referenced_at or fact.created_at
        scored.append((score, recency, fact))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[:limit]]


async def get_relevant_memory_facts(
    db: AsyncSession,
    *,
    user_id: str,
    message_text: str,
    limit: int = DEFAULT_RELEVANT_FACT_LIMIT,
) -> list[UserMemoryFact]:
    result = await db.execute(
        select(UserMemoryFact).where(UserMemoryFact.user_id == user_id)
    )
    facts = list(result.scalars().all())
    relevant = rank_relevant_facts(facts, message_text, limit=limit)
    if not relevant and limit > 0:
        # Vague recall questions (for example, "what am I working on again?")
        # may share no literal tokens with a stored fact. Fall back to recent
        # facts so the LLM can decide which of a small context is relevant.
        relevant = sorted(
            facts,
            key=lambda fact: fact.last_referenced_at or fact.created_at,
            reverse=True,
        )[:limit]
    referenced_at = utc_now()
    for fact in relevant:
        fact.last_referenced_at = referenced_at
    return relevant


async def remember_message_facts(
    db: AsyncSession,
    *,
    user_id: str,
    message_text: str,
) -> list[UserMemoryFact]:
    logger.info(
        "[memory] extraction received user_id=%s message=%r",
        user_id,
        message_text,
    )
    candidates = extract_memory_candidates(message_text)
    if not candidates:
        logger.info(
            "[memory] extraction completed user_id=%s candidates=0 stored=0",
            user_id,
        )
        return []

    result = await db.execute(
        select(UserMemoryFact).where(UserMemoryFact.user_id == user_id)
    )
    known_facts = list(result.scalars().all())
    created: list[UserMemoryFact] = []
    for candidate in candidates:
        duplicate = next(
            (
                fact
                for fact in [*known_facts, *created]
                if facts_are_duplicates(candidate.fact_text, fact.fact_text)
            ),
            None,
        )
        if duplicate is not None:
            logger.info(
                "[memory] storage decision=duplicate user_id=%s candidate=%r "
                "existing_fact_id=%s existing=%r",
                user_id,
                candidate.fact_text,
                duplicate.id,
                duplicate.fact_text,
            )
            continue
        fact = UserMemoryFact(
            id=str(uuid4()),
            user_id=user_id,
            fact_text=candidate.fact_text,
            category=candidate.category,
        )
        db.add(fact)
        created.append(fact)
        logger.info(
            "[memory] storage decision=created user_id=%s fact_id=%s "
            "category=%s fact=%r",
            user_id,
            fact.id,
            fact.category,
            fact.fact_text,
        )
    logger.info(
        "[memory] extraction completed user_id=%s candidates=%d stored=%d",
        user_id,
        len(candidates),
        len(created),
    )
    return created


def _meaningful_tokens(normalized_text: str) -> set[str]:
    tokens = {
        token
        for token in normalized_text.split()
        if len(token) > 1 and token not in _STOP_WORDS
    }
    cjk_text = "".join(_CJK_CHARACTER.findall(normalized_text))
    tokens.update(
        cjk_text[index : index + 2] for index in range(max(0, len(cjk_text) - 1))
    )
    return tokens
