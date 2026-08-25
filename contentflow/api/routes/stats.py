from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from core.database import get_db
from models.post import Post
from models.source import Source
from models.ai_request import AIRequest

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    # Count sources
    sources_result = await db.execute(
        select(func.count(Source.id)).where(Source.user_id == user_id)
    )
    total_sources = sources_result.scalar() or 0

    # Count posts by status
    new_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user_id,
            Post.status == "new",
        )
    )
    new_posts = new_result.scalar() or 0

    draft_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user_id,
            Post.status == "draft",
        )
    )
    draft_posts = draft_result.scalar() or 0

    published_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user_id,
            Post.status == "published",
            Post.published_at >= datetime.utcnow() - timedelta(days=1),
        )
    )
    published_today = published_result.scalar() or 0

    # Count AI requests
    ai_result = await db.execute(
        select(func.count(AIRequest.id)).where(
            AIRequest.user_id == user_id,
            AIRequest.created_at >= datetime.utcnow() - timedelta(days=1),
        )
    )
    ai_requests_today = ai_result.scalar() or 0

    return {
        "total_sources": total_sources,
        "new_posts": new_posts,
        "draft_posts": draft_posts,
        "published_today": published_today,
        "ai_requests_today": ai_requests_today,
    }
