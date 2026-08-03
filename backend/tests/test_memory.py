from datetime import datetime, timedelta, timezone

import pytest

from app.models.user_memory_fact import UserMemoryFact
from app.services.conversation.llm_client import LLMClient
from app.services.conversation.memory import (
    extract_memory_candidates,
    facts_are_duplicates,
    get_relevant_memory_facts,
    rank_relevant_facts,
    remember_message_facts,
)


def _fact(
    fact_id: str,
    text: str,
    *,
    created_at: datetime,
) -> UserMemoryFact:
    return UserMemoryFact(
        id=fact_id,
        user_id="user-1",
        fact_text=text,
        category="preference",
        created_at=created_at,
    )


def test_extracts_durable_facts_but_ignores_transient_states() -> None:
    candidates = extract_memory_candidates(
        "I'm working on a school project. I prefer concise answers. I'm tired today."
    )

    assert [(item.category, item.fact_text) for item in candidates] == [
        ("project", "I'm working on a school project"),
        ("preference", "I prefer concise answers"),
    ]

    mandarin = extract_memory_candidates("我最喜欢机器学习。")
    assert [(item.category, item.fact_text) for item in mandarin] == [
        ("preference", "我最喜欢机器学习")
    ]


def test_extracts_reported_student_portfolio_fact_exactly() -> None:
    message = "I'm a software engineering student building an AI portfolio project"

    candidates = extract_memory_candidates(message)

    assert [(item.category, item.fact_text) for item in candidates] == [
        ("profile", message)
    ]


def test_duplicate_detection_normalizes_contractions_and_fillers() -> None:
    assert facts_are_duplicates(
        "I'm working on a school project",
        "I am working on the school project",
    )
    assert not facts_are_duplicates(
        "I prefer concise answers",
        "I love machine learning",
    )


def test_relevance_ranks_keyword_matches_and_ignores_unrelated_facts() -> None:
    now = datetime.now(timezone.utc)
    project = _fact(
        "project",
        "I'm working on a machine learning school project",
        created_at=now - timedelta(days=2),
    )
    preference = _fact(
        "preference",
        "I prefer concise answers",
        created_at=now - timedelta(days=1),
    )

    relevant = rank_relevant_facts(
        [preference, project],
        "Can you help with my machine learning project?",
    )

    assert relevant == [project]


@pytest.mark.asyncio
async def test_retrieval_marks_only_selected_facts_as_referenced() -> None:
    now = datetime.now(timezone.utc)
    project = _fact(
        "project",
        "I'm working on a robotics project",
        created_at=now,
    )
    preference = _fact(
        "preference",
        "I prefer concise answers",
        created_at=now,
    )

    class FakeScalars:
        def all(self) -> list[UserMemoryFact]:
            return [preference, project]

    class FakeResult:
        def scalars(self) -> FakeScalars:
            return FakeScalars()

    class FakeDb:
        async def execute(self, _query: object) -> FakeResult:
            return FakeResult()

    relevant = await get_relevant_memory_facts(
        FakeDb(),  # type: ignore[arg-type]
        user_id="user-1",
        message_text="How is my robotics project going?",
    )

    assert relevant == [project]
    assert project.last_referenced_at is not None
    assert preference.last_referenced_at is None


@pytest.mark.asyncio
async def test_vague_recall_falls_back_to_recent_facts() -> None:
    now = datetime.now(timezone.utc)
    project = _fact(
        "project",
        "I'm a software engineering student building an AI portfolio project",
        created_at=now,
    )

    class FakeScalars:
        def all(self) -> list[UserMemoryFact]:
            return [project]

    class FakeResult:
        def scalars(self) -> FakeScalars:
            return FakeScalars()

    class FakeDb:
        async def execute(self, _query: object) -> FakeResult:
            return FakeResult()

    relevant = await get_relevant_memory_facts(
        FakeDb(),  # type: ignore[arg-type]
        user_id="user-1",
        message_text="What am I working on again?",
    )

    assert relevant == [project]
    assert project.last_referenced_at is not None


@pytest.mark.asyncio
async def test_stored_fact_answers_later_question_in_a_new_conversation() -> None:
    class FakeScalars:
        def __init__(self, facts: list[UserMemoryFact]) -> None:
            self.facts = facts

        def all(self) -> list[UserMemoryFact]:
            return self.facts

    class FakeResult:
        def __init__(self, facts: list[UserMemoryFact]) -> None:
            self.facts = facts

        def scalars(self) -> FakeScalars:
            return FakeScalars(self.facts)

    class FakeDb:
        facts: list[UserMemoryFact]

        def __init__(self) -> None:
            self.facts = []

        async def execute(self, _query: object) -> FakeResult:
            return FakeResult(self.facts)

        def add(self, fact: UserMemoryFact) -> None:
            fact.created_at = datetime.now(timezone.utc)
            self.facts.append(fact)

    fact_message = (
        "I'm a software engineering student building an AI portfolio project"
    )
    db = FakeDb()
    stored = await remember_message_facts(
        db,  # type: ignore[arg-type]
        user_id="user-1",
        message_text=fact_message,
    )

    # Only the later question is sent as LLM history, mirroring a new conversation.
    recalled = await get_relevant_memory_facts(
        db,  # type: ignore[arg-type]
        user_id="user-1",
        message_text="What am I working on again?",
    )
    reply = await LLMClient(api_key=None, mock_mode=True).generate_reply(
        user_name="Ada",
        detected_language="en",
        detected_emotion=None,
        is_live=True,
        messages=[{"role": "user", "content": "What am I working on again?"}],
        should_greet=True,
        memory_facts=[fact.fact_text for fact in recalled],
    )

    assert [fact.fact_text for fact in stored] == [fact_message]
    assert "AI portfolio project" in reply


@pytest.mark.asyncio
async def test_remember_message_facts_avoids_existing_duplicates() -> None:
    existing = _fact(
        "existing",
        "I am working on a school project",
        created_at=datetime.now(timezone.utc),
    )

    class FakeScalars:
        def all(self) -> list[UserMemoryFact]:
            return [existing]

    class FakeResult:
        def scalars(self) -> FakeScalars:
            return FakeScalars()

    class FakeDb:
        added: list[UserMemoryFact] = []

        async def execute(self, _query: object) -> FakeResult:
            return FakeResult()

        def add(self, fact: UserMemoryFact) -> None:
            self.added.append(fact)

    db = FakeDb()
    created = await remember_message_facts(
        db,  # type: ignore[arg-type]
        user_id="user-1",
        message_text=("I'm working on the school project. I prefer concise answers."),
    )

    assert [fact.fact_text for fact in created] == ["I prefer concise answers"]
    assert db.added == created
