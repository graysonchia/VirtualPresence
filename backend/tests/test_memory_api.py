from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app, fastapi_app
from app.models.user import User
from app.models.user_memory_fact import UserMemoryFact


def test_memory_facts_can_be_listed_and_deleted() -> None:
    fact = UserMemoryFact(
        id="fact-1",
        user_id="user-1",
        fact_text="I prefer concise answers",
        category="preference",
        created_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )

    class FakeScalars:
        def all(self) -> list[UserMemoryFact]:
            return [fact]

    class FakeResult:
        def scalars(self) -> FakeScalars:
            return FakeScalars()

    class FakeDb:
        deleted: UserMemoryFact | None = None
        committed = False

        async def get(self, model: object, item_id: str) -> object | None:
            if model is User and item_id == "user-1":
                return object()
            if model is UserMemoryFact and item_id == fact.id:
                return fact
            return None

        async def execute(self, _query: object) -> FakeResult:
            return FakeResult()

        async def delete(self, item: UserMemoryFact) -> None:
            self.deleted = item

        async def commit(self) -> None:
            self.committed = True

    db = FakeDb()

    async def override_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            listing = client.get("/memory/users/user-1/facts")
            deletion = client.delete("/memory/users/user-1/facts/fact-1")
    finally:
        fastapi_app.dependency_overrides.clear()

    assert listing.status_code == 200
    assert listing.json() == {
        "user_id": "user-1",
        "facts": [
            {
                "id": "fact-1",
                "user_id": "user-1",
                "fact_text": "I prefer concise answers",
                "category": "preference",
                "created_at": "2026-07-31T00:00:00Z",
                "last_referenced_at": None,
            }
        ],
        "count": 1,
    }
    assert deletion.status_code == 204
    assert db.deleted is fact
    assert db.committed
