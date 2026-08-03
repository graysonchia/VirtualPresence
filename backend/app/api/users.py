from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserSettingsResponse, UserSettingsUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.patch(
    "/{user_id}/settings",
    response_model=UserSettingsResponse,
)
async def update_user_settings(
    user_id: str,
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    user.preferred_voice_gender = payload.preferred_voice_gender
    await db.commit()
    return UserSettingsResponse(
        user_id=user.id,
        preferred_voice_gender=user.preferred_voice_gender,
    )
