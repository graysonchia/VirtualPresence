from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryFactItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    fact_text: str
    category: str
    created_at: datetime
    last_referenced_at: datetime | None


class MemoryFactListResponse(BaseModel):
    user_id: str
    facts: list[MemoryFactItem]
    count: int
