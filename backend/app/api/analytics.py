from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import (
    AnalyticsOverview,
    EmotionDistributionResponse,
    RecognitionTrendsResponse,
    UsagePatternsResponse,
)
from app.services.analytics import (
    get_emotion_distribution,
    get_overview_metrics,
    get_recognition_trends,
    get_usage_patterns,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def read_overview(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    return await get_overview_metrics(db)


@router.get("/recognition-trends", response_model=RecognitionTrendsResponse)
async def read_recognition_trends(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> RecognitionTrendsResponse:
    return await get_recognition_trends(db, days=days)


@router.get(
    "/emotion-distribution",
    response_model=EmotionDistributionResponse,
)
async def read_emotion_distribution(
    db: AsyncSession = Depends(get_db),
) -> EmotionDistributionResponse:
    return await get_emotion_distribution(db)


@router.get("/usage-patterns", response_model=UsagePatternsResponse)
async def read_usage_patterns(
    db: AsyncSession = Depends(get_db),
) -> UsagePatternsResponse:
    return await get_usage_patterns(db)
