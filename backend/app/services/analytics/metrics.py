from datetime import datetime, time, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_message import ConversationMessage
from app.models.interaction_session import InteractionSession
from app.models.recognition_event import RecognitionEvent, RecognitionOutcome
from app.models.user import User
from app.models.user_memory_fact import UserMemoryFact
from app.schemas.analytics import (
    AnalyticsOverview,
    DailyUsagePoint,
    EmotionDistributionItem,
    EmotionDistributionResponse,
    HourlyUsagePoint,
    RecognitionTrendPoint,
    RecognitionTrendsResponse,
    UsagePatternsResponse,
)


def _message_rollup():
    return (
        select(
            ConversationMessage.session_id.label("session_id"),
            func.count(ConversationMessage.id).label("message_count"),
            func.max(ConversationMessage.timestamp).label("last_message_at"),
        )
        .group_by(ConversationMessage.session_id)
        .subquery()
    )


def _session_activity_at(message_rollup):
    return func.coalesce(
        InteractionSession.last_activity_at,
        message_rollup.c.last_message_at,
    )


def _session_duration_seconds(message_rollup):
    activity_at = _session_activity_at(message_rollup)
    return func.greatest(
        0.0,
        func.extract("epoch", activity_at - InteractionSession.started_at),
    )


async def get_overview_metrics(db: AsyncSession) -> AnalyticsOverview:
    message_rollup = _message_rollup()
    activity_at = _session_activity_at(message_rollup)
    duration_seconds = _session_duration_seconds(message_rollup)
    session_row = (
        (
            await db.execute(
                select(
                    func.count(InteractionSession.id).label("total_sessions"),
                    func.coalesce(
                        func.sum(InteractionSession.message_count), 0
                    ).label("total_messages"),
                    func.coalesce(
                        func.avg(duration_seconds).filter(
                            activity_at.is_not(None)
                        ),
                        0.0,
                    ).label("average_session_length_seconds"),
                    func.coalesce(
                        func.avg(InteractionSession.message_count),
                        0.0,
                    ).label("average_messages_per_session"),
                ).outerjoin(
                    message_rollup,
                    message_rollup.c.session_id == InteractionSession.id,
                )
            )
        )
        .mappings()
        .one()
    )
    recognition_row = (
        (
            await db.execute(
                select(
                    func.count(RecognitionEvent.id).label("total_attempts"),
                    func.coalesce(func.avg(RecognitionEvent.confidence), 0.0).label(
                        "average_confidence"
                    ),
                    func.coalesce(
                        func.avg(
                            case(
                                (
                                    RecognitionEvent.outcome
                                    == RecognitionOutcome.RECOGNIZED,
                                    1.0,
                                ),
                                else_=0.0,
                            )
                        ),
                        0.0,
                    ).label("success_rate"),
                    func.coalesce(
                        func.avg(
                            case((RecognitionEvent.is_live.is_(True), 1.0), else_=0.0)
                        ),
                        0.0,
                    ).label("liveness_pass_rate"),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    RecognitionEvent.outcome
                                    == RecognitionOutcome.SPOOF_DETECTED,
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("spoof_count"),
                )
            )
        )
        .mappings()
        .one()
    )
    memory_row = (
        (
            await db.execute(
                select(
                    func.count(UserMemoryFact.id).label("total_facts"),
                    func.count(UserMemoryFact.last_referenced_at).label(
                        "referenced_facts"
                    ),
                )
            )
        )
        .mappings()
        .one()
    )
    total_users = int(
        (await db.execute(select(func.count(User.id)))).scalar_one()
    )
    total_sessions = int(session_row["total_sessions"] or 0)
    referenced_facts = int(memory_row["referenced_facts"] or 0)
    liveness_pass_rate = float(
        recognition_row["liveness_pass_rate"] or 0.0
    )
    return AnalyticsOverview(
        total_users=total_users,
        total_sessions=total_sessions,
        total_messages=int(session_row["total_messages"] or 0),
        total_recognition_attempts=int(recognition_row["total_attempts"] or 0),
        average_session_length_seconds=float(
            session_row["average_session_length_seconds"] or 0.0
        ),
        average_messages_per_session=float(
            session_row["average_messages_per_session"] or 0.0
        ),
        recognition_success_rate=float(recognition_row["success_rate"] or 0.0),
        average_match_confidence=float(
            recognition_row["average_confidence"] or 0.0
        ),
        liveness_pass_rate=liveness_pass_rate,
        liveness_fail_rate=(
            1.0 - liveness_pass_rate
            if int(recognition_row["total_attempts"] or 0)
            else 0.0
        ),
        spoof_detection_count=int(recognition_row["spoof_count"] or 0),
        total_memory_facts=int(memory_row["total_facts"] or 0),
        referenced_memory_facts=referenced_facts,
        average_referenced_facts_per_session=(
            referenced_facts / total_sessions if total_sessions else 0.0
        ),
    )


async def get_recognition_trends(
    db: AsyncSession,
    *,
    days: int,
) -> RecognitionTrendsResponse:
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)
    cutoff = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    event_date = func.date(func.timezone("UTC", RecognitionEvent.timestamp))
    rows = (
        (
            await db.execute(
                select(
                    event_date.label("date"),
                    func.count(RecognitionEvent.id).label("total_attempts"),
                    func.sum(
                        case(
                            (
                                RecognitionEvent.outcome
                                == RecognitionOutcome.RECOGNIZED,
                                1,
                            ),
                            else_=0,
                        )
                    ).label("recognized_count"),
                    func.sum(
                        case(
                            (
                                RecognitionEvent.outcome
                                == RecognitionOutcome.SPOOF_DETECTED,
                                1,
                            ),
                            else_=0,
                        )
                    ).label("spoof_count"),
                    func.avg(RecognitionEvent.confidence).label(
                        "average_confidence"
                    ),
                    func.avg(
                        case((RecognitionEvent.is_live.is_(True), 1.0), else_=0.0)
                    ).label("liveness_pass_rate"),
                    func.sum(
                        case((RecognitionEvent.confidence < 0.5, 1), else_=0)
                    ).label("low_confidence_count"),
                    func.sum(
                        case(
                            (
                                RecognitionEvent.confidence.between(0.5, 0.799999),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("medium_confidence_count"),
                    func.sum(
                        case((RecognitionEvent.confidence >= 0.8, 1), else_=0)
                    ).label("high_confidence_count"),
                )
                .where(RecognitionEvent.timestamp >= cutoff)
                .group_by(event_date)
                .order_by(event_date)
            )
        )
        .mappings()
        .all()
    )
    rows_by_date = {row["date"]: row for row in rows}
    points: list[RecognitionTrendPoint] = []
    for offset in range(days):
        current_date = start_date + timedelta(days=offset)
        row = rows_by_date.get(current_date)
        points.append(
            RecognitionTrendPoint(
                date=current_date,
                total_attempts=int(row["total_attempts"] or 0) if row else 0,
                recognized_count=int(row["recognized_count"] or 0) if row else 0,
                spoof_detection_count=int(row["spoof_count"] or 0) if row else 0,
                average_match_confidence=(
                    float(row["average_confidence"])
                    if row and row["average_confidence"] is not None
                    else None
                ),
                liveness_pass_rate=(
                    float(row["liveness_pass_rate"])
                    if row and row["liveness_pass_rate"] is not None
                    else None
                ),
                liveness_fail_rate=(
                    1.0 - float(row["liveness_pass_rate"])
                    if row and row["liveness_pass_rate"] is not None
                    else None
                ),
                low_confidence_count=(
                    int(row["low_confidence_count"] or 0) if row else 0
                ),
                medium_confidence_count=(
                    int(row["medium_confidence_count"] or 0) if row else 0
                ),
                high_confidence_count=(
                    int(row["high_confidence_count"] or 0) if row else 0
                ),
            )
        )
    return RecognitionTrendsResponse(
        days=days,
        start_date=start_date,
        end_date=end_date,
        points=points,
    )


async def get_emotion_distribution(
    db: AsyncSession,
) -> EmotionDistributionResponse:
    rows = (
        (
            await db.execute(
                select(
                    RecognitionEvent.detected_emotion.label("emotion"),
                    func.count(RecognitionEvent.id).label("count"),
                )
                .where(RecognitionEvent.detected_emotion.is_not(None))
                .group_by(RecognitionEvent.detected_emotion)
                .order_by(func.count(RecognitionEvent.id).desc())
            )
        )
        .mappings()
        .all()
    )
    total = sum(int(row["count"]) for row in rows)
    return EmotionDistributionResponse(
        total_observations=total,
        emotions=[
            EmotionDistributionItem(
                emotion=str(row["emotion"]),
                count=int(row["count"]),
                percentage=int(row["count"]) / total if total else 0.0,
            )
            for row in rows
        ],
    )


async def get_usage_patterns(db: AsyncSession) -> UsagePatternsResponse:
    message_rollup = _message_rollup()
    activity_at = _session_activity_at(message_rollup)
    duration_seconds = _session_duration_seconds(message_rollup)
    session_date = func.date(func.timezone("UTC", InteractionSession.started_at))
    daily_session_rows = (
        (
            await db.execute(
                select(
                    session_date.label("date"),
                    func.count(InteractionSession.id).label("sessions"),
                    func.count(InteractionSession.id)
                    .filter(activity_at.is_not(None))
                    .label("sessions_with_activity"),
                    func.coalesce(
                        func.sum(InteractionSession.message_count),
                        0,
                    ).label("messages"),
                    func.coalesce(
                        func.avg(InteractionSession.message_count),
                        0.0,
                    ).label("average_messages_per_session"),
                    func.coalesce(
                        func.avg(duration_seconds).filter(
                            activity_at.is_not(None)
                        ),
                        0.0,
                    ).label("average_session_length_seconds"),
                )
                .outerjoin(
                    message_rollup,
                    message_rollup.c.session_id == InteractionSession.id,
                )
                .group_by(session_date)
                .order_by(session_date)
            )
        )
        .mappings()
        .all()
    )
    session_hour = func.extract(
        "hour", func.timezone("UTC", InteractionSession.started_at)
    )
    hourly_session_rows = (
        (
            await db.execute(
                select(
                    session_hour.label("hour"),
                    func.count(InteractionSession.id).label("sessions"),
                    func.coalesce(
                        func.sum(InteractionSession.message_count), 0
                    ).label("messages"),
                )
                .group_by(session_hour)
                .order_by(session_hour)
            )
        )
        .mappings()
        .all()
    )

    session_days = {row["date"]: row for row in daily_session_rows}
    daily = [
        DailyUsagePoint(
            date=current_date,
            sessions=int(session_days.get(current_date, {}).get("sessions", 0)),
            messages=int(session_days[current_date]["messages"] or 0),
            average_messages_per_session=float(
                session_days.get(current_date, {}).get(
                    "average_messages_per_session", 0.0
                )
                or 0.0
            ),
            average_session_length_seconds=float(
                session_days.get(current_date, {}).get(
                    "average_session_length_seconds", 0.0
                )
                or 0.0
            ),
        )
        for current_date in sorted(session_days)
    ]
    sessions_by_hour = {
        int(row["hour"]): int(row["sessions"]) for row in hourly_session_rows
    }
    messages_by_hour = {
        int(row["hour"]): int(row["messages"]) for row in hourly_session_rows
    }
    hourly = [
        HourlyUsagePoint(
            hour=hour,
            sessions=sessions_by_hour.get(hour, 0),
            messages=messages_by_hour.get(hour, 0),
        )
        for hour in range(24)
    ]
    total_sessions = sum(item.sessions for item in daily)
    total_messages = sum(item.messages for item in daily)
    observed_session_count = sum(
        int(row["sessions_with_activity"] or 0) for row in daily_session_rows
    )
    weighted_duration = sum(
        float(row["average_session_length_seconds"] or 0.0)
        * int(row["sessions_with_activity"] or 0)
        for row in daily_session_rows
    )
    active_hours = [item for item in hourly if item.sessions or item.messages]
    most_active_hour = (
        max(active_hours, key=lambda item: (item.sessions, item.messages)).hour
        if active_hours
        else None
    )
    return UsagePatternsResponse(
        total_sessions=total_sessions,
        total_messages=total_messages,
        average_messages_per_session=(
            total_messages / total_sessions if total_sessions else 0.0
        ),
        average_session_length_seconds=(
            weighted_duration / observed_session_count
            if observed_session_count
            else 0.0
        ),
        most_active_hour=most_active_hour,
        daily=daily,
        hourly=hourly,
    )
