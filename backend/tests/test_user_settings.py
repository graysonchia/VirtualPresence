from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app, fastapi_app
from app.models.user import VoiceGender


def test_voice_gender_preference_can_be_updated() -> None:
    class FakeUser:
        id = "user-1"
        preferred_voice_gender = VoiceGender.MALE

    class FakeDb:
        user = FakeUser()
        committed = False

        async def get(self, _model: object, user_id: str) -> FakeUser | None:
            return self.user if user_id == self.user.id else None

        async def commit(self) -> None:
            self.committed = True

    db = FakeDb()

    async def override_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.patch(
                "/users/user-1/settings",
                json={"preferred_voice_gender": "female"},
            )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "preferred_voice_gender": "female",
    }
    assert db.user.preferred_voice_gender == VoiceGender.FEMALE
    assert db.committed
