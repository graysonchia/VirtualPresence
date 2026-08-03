from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.api.analytics as analytics_api
from app.core.database import get_db
from app.main import app, fastapi_app
from app.schemas.analytics import (
    AnalyticsOverview,
    EmotionDistributionItem,
    EmotionDistributionResponse,
    RecognitionTrendPoint,
    RecognitionTrendsResponse,
    UsagePatternsResponse,
)
from app.services.analytics.metrics import (
    get_emotion_distribution,
    get_overview_metrics,
    get_recognition_trends,
    get_usage_patterns,
)


class FakeResult:
    def __init__(
        self,
        *,
        one: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
        scalar: object | None = None,
    ) -> None:
        self._one = one
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> "FakeResult":
        return self

    def one(self) -> dict[str, object]:
        assert self._one is not None
        return self._one

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def scalar_one(self) -> object:
        return self._scalar


class FakeDb:
    def __init__(self, results: list[FakeResult]) -> None:
        self.results = results

    async def execute(self, _query: object) -> FakeResult:
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_overview_aggregates_usage_recognition_and_memory() -> None:
    db = FakeDb(
        [
            FakeResult(
                one={
                    "total_sessions": 4,
                    "total_messages": 18,
                    "average_session_length_seconds": 125.5,
                    "average_messages_per_session": 4.5,
                }
            ),
            FakeResult(
                one={
                    "total_attempts": 10,
                    "average_confidence": 0.82,
                    "success_rate": 0.7,
                    "liveness_pass_rate": 0.8,
                    "spoof_count": 2,
                }
            ),
            FakeResult(one={"total_facts": 6, "referenced_facts": 3}),
            FakeResult(scalar=5),
        ]
    )

    overview = await get_overview_metrics(db)  # type: ignore[arg-type]

    assert overview.total_users == 5
    assert overview.total_sessions == 4
    assert overview.total_messages == 18
    assert overview.recognition_success_rate == pytest.approx(0.7)
    assert overview.average_match_confidence == pytest.approx(0.82)
    assert overview.liveness_fail_rate == pytest.approx(0.2)
    assert overview.spoof_detection_count == 2
    assert overview.total_memory_facts == 6
    assert overview.average_referenced_facts_per_session == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_recognition_trends_fill_empty_days_and_confidence_buckets() -> None:
    today = datetime.now(timezone.utc).date()
    db = FakeDb(
        [
            FakeResult(
                rows=[
                    {
                        "date": today,
                        "total_attempts": 5,
                        "recognized_count": 3,
                        "spoof_count": 1,
                        "average_confidence": 0.76,
                        "liveness_pass_rate": 0.8,
                        "low_confidence_count": 1,
                        "medium_confidence_count": 2,
                        "high_confidence_count": 2,
                    }
                ]
            )
        ]
    )

    trends = await get_recognition_trends(  # type: ignore[arg-type]
        db,
        days=3,
    )

    assert len(trends.points) == 3
    assert trends.points[0].total_attempts == 0
    assert trends.points[-1].date == today
    assert trends.points[-1].average_match_confidence == pytest.approx(0.76)
    assert trends.points[-1].liveness_fail_rate == pytest.approx(0.2)
    assert trends.points[-1].high_confidence_count == 2


@pytest.mark.asyncio
async def test_emotion_distribution_calculates_percentages() -> None:
    db = FakeDb(
        [
            FakeResult(
                rows=[
                    {"emotion": "happy", "count": 3},
                    {"emotion": "neutral", "count": 1},
                ]
            )
        ]
    )

    distribution = await get_emotion_distribution(  # type: ignore[arg-type]
        db
    )

    assert distribution.total_observations == 4
    assert distribution.emotions[0].percentage == pytest.approx(0.75)
    assert distribution.emotions[1].percentage == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_usage_patterns_combine_daily_and_hourly_activity() -> None:
    today = datetime.now(timezone.utc).date()
    db = FakeDb(
        [
            FakeResult(
                rows=[
                    {
                        "date": today,
                        "sessions": 2,
                        "sessions_with_activity": 2,
                        "messages": 6,
                        "average_messages_per_session": 3.0,
                        "average_session_length_seconds": 90.0,
                    }
                ]
            ),
            FakeResult(rows=[{"hour": 14, "sessions": 2, "messages": 6}]),
        ]
    )

    usage = await get_usage_patterns(db)  # type: ignore[arg-type]

    assert usage.total_sessions == 2
    assert usage.total_messages == 6
    assert usage.average_messages_per_session == 3
    assert usage.average_session_length_seconds == 90
    assert usage.most_active_hour == 14
    assert usage.daily[0].messages == 6
    assert len(usage.hourly) == 24
    assert usage.hourly[14].sessions == 2


def test_analytics_endpoints_return_typed_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = datetime.now(timezone.utc).date()

    async def override_db():
        yield object()

    async def fake_overview(_db: object) -> AnalyticsOverview:
        return AnalyticsOverview(total_users=3, total_sessions=8)

    async def fake_trends(
        _db: object,
        *,
        days: int,
    ) -> RecognitionTrendsResponse:
        return RecognitionTrendsResponse(
            days=days,
            start_date=today,
            end_date=today,
            points=[RecognitionTrendPoint(date=today, total_attempts=2)],
        )

    async def fake_emotions(_db: object) -> EmotionDistributionResponse:
        return EmotionDistributionResponse(
            total_observations=2,
            emotions=[
                EmotionDistributionItem(
                    emotion="happy",
                    count=2,
                    percentage=1.0,
                )
            ],
        )

    async def fake_usage(_db: object) -> UsagePatternsResponse:
        return UsagePatternsResponse(
            total_sessions=0,
            total_messages=0,
            average_messages_per_session=0,
            average_session_length_seconds=0,
            daily=[],
            hourly=[],
        )

    monkeypatch.setattr(analytics_api, "get_overview_metrics", fake_overview)
    monkeypatch.setattr(analytics_api, "get_recognition_trends", fake_trends)
    monkeypatch.setattr(
        analytics_api,
        "get_emotion_distribution",
        fake_emotions,
    )
    monkeypatch.setattr(analytics_api, "get_usage_patterns", fake_usage)
    fastapi_app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            overview = client.get("/analytics/overview")
            trends = client.get("/analytics/recognition-trends?days=7")
            emotions = client.get("/analytics/emotion-distribution")
            usage = client.get("/analytics/usage-patterns")
            invalid = client.get("/analytics/recognition-trends?days=0")
    finally:
        fastapi_app.dependency_overrides.clear()

    assert overview.status_code == 200
    assert overview.json()["total_users"] == 3
    assert trends.status_code == 200
    assert trends.json()["days"] == 7
    assert emotions.json()["emotions"][0]["emotion"] == "happy"
    assert usage.status_code == 200
    assert invalid.status_code == 422
