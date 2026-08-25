from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.ai_usage import AIUsage
from models.ai_request import AIRequest

router = APIRouter()


class AIUsageResponse(BaseModel):
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float

    class Config:
        from_attributes = True


@router.get("/usage")
async def get_ai_usage(user_id: int, period: str = "today", db: AsyncSession = Depends(get_db)):
    """Get AI usage statistics for a period."""
    # TODO: Implement period filtering
    result = await db.execute(
        select(AIUsage)
        .where(AIUsage.user_id == user_id)
        .order_by(AIUsage.date.desc())
        .limit(30)
    )
    usage = result.scalars().all()
    return [AIUsageResponse.from_orm(u) for u in usage]


@router.get("/requests")
async def get_ai_requests(user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent AI requests."""
    result = await db.execute(
        select(AIRequest)
        .where(AIRequest.user_id == user_id)
        .order_by(AIRequest.created_at.desc())
        .limit(limit)
    )
    requests = result.scalars().all()
    return requests


@router.post("/analyze")
async def analyze_content(user_id: int, text: str, db: AsyncSession = Depends(get_db)):
    """Analyze content using AI."""
    # TODO: Queue AI analysis task
    return {"message": "Analysis queued"}


@router.post("/rewrite")
async def rewrite_content(user_id: int, text: str, style: str = "neutral", db: AsyncSession = Depends(get_db)):
    """Rewrite content using AI."""
    # TODO: Queue AI rewrite task
    return {"message": "Rewrite queued"}
