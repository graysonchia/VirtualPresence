from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.user_memory_fact import UserMemoryFact
from app.schemas.memory import MemoryFactItem, MemoryFactListResponse


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get(
    "/users/{user_id}/facts",
    response_model=MemoryFactListResponse,
)
async def list_memory_facts(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> MemoryFactListResponse:
    if await db.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    result = await db.execute(
        select(UserMemoryFact)
        .where(UserMemoryFact.user_id == user_id)
        .order_by(UserMemoryFact.created_at.desc())
    )
    facts = list(result.scalars().all())
    return MemoryFactListResponse(
        user_id=user_id,
        facts=[MemoryFactItem.model_validate(fact) for fact in facts],
        count=len(facts),
    )


@router.delete(
    "/users/{user_id}/facts/{fact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_memory_fact(
    user_id: str,
    fact_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if await db.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    fact = await db.get(UserMemoryFact, fact_id)
    if fact is None or fact.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory fact not found.",
        )
    await db.delete(fact)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
