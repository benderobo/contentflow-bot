from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from core.database import get_db
from models.post import Post
from models.source import Source
from models.source_item import SourceItem
from models.channel import Channel
from models.publish_job import PublishJob
from models.ai_request import AIRequest
from api.dependencies import verify_service_auth

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


# ===== ANALYTICS ENDPOINTS =====

@router.get("/overview")
async def get_stats_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get overview statistics for user."""
    from utils.auth import verify_user_id

    user_id = request.query_params.get("user_id", type=int)
    user_signature = request.query_params.get("user_signature")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Count posts
    posts_result = await db.execute(
        select(func.count(Post.id)).where(Post.user_id == user_id)
    )
    posts_created = posts_result.scalar() or 0

    published_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user_id,
            Post.status == "published"
        )
    )
    posts_published = published_result.scalar() or 0

    # Count scheduled
    scheduled_result = await db.execute(
        select(func.count(PublishJob.id)).where(
            PublishJob.status == "pending"
        )
    )
    posts_scheduled = scheduled_result.scalar() or 0

    # Count sources and channels
    sources_result = await db.execute(
        select(func.count(Source.id)).where(Source.user_id == user_id)
    )
    sources_count = sources_result.scalar() or 0

    channels_result = await db.execute(
        select(func.count(Channel.id)).where(Channel.user_id == user_id)
    )
    channels_count = channels_result.scalar() or 0

    return {
        "posts_created": posts_created,
        "posts_published": posts_published,
        "posts_scheduled": posts_scheduled,
        "sources_count": sources_count,
        "channels_count": channels_count,
    }


@router.get("/timeline")
async def get_stats_timeline(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get timeline statistics."""
    from utils.auth import verify_user_id

    user_id = request.query_params.get("user_id", type=int)
    user_signature = request.query_params.get("user_signature")
    period = request.query_params.get("period", "7d")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Parse period
    if period == "30d":
        days = 30
    else:
        days = 7

    timeline = []
    for i in range(days, 0, -1):
        date = (datetime.utcnow() - timedelta(days=i)).date()

        # Count published posts
        published_result = await db.execute(
            select(func.count(Post.id)).where(
                Post.user_id == user_id,
                Post.status == "published",
                func.date(Post.published_at) == date
            )
        )
        published = published_result.scalar() or 0

        # Count scheduled
        scheduled_result = await db.execute(
            select(func.count(PublishJob.id)).where(
                PublishJob.status == "pending",
                func.date(PublishJob.scheduled_at) == date
            )
        )
        scheduled = scheduled_result.scalar() or 0

        timeline.append({
            "date": str(date),
            "published": published,
            "scheduled": scheduled,
        })

    return timeline


@router.get("/by-channel")
async def get_stats_by_channel(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get statistics grouped by channel."""
    from utils.auth import verify_user_id

    user_id = request.query_params.get("user_id", type=int)
    user_signature = request.query_params.get("user_signature")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Get user's channels
    channels_result = await db.execute(
        select(Channel).where(Channel.user_id == user_id)
    )
    channels = channels_result.scalars().all()

    stats = []
    for channel in channels:
        published_result = await db.execute(
            select(func.count(PublishJob.id)).where(
                PublishJob.channel_id == channel.id,
                PublishJob.status == "published"
            )
        )
        published = published_result.scalar() or 0

        scheduled_result = await db.execute(
            select(func.count(PublishJob.id)).where(
                PublishJob.channel_id == channel.id,
                PublishJob.status == "pending"
            )
        )
        scheduled = scheduled_result.scalar() or 0

        stats.append({
            "channel_id": channel.id,
            "channel_name": channel.name,
            "published_count": published,
            "scheduled_count": scheduled,
        })

    return stats


@router.get("/by-source")
async def get_stats_by_source(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get statistics grouped by source."""
    from utils.auth import verify_user_id

    user_id = request.query_params.get("user_id", type=int)
    user_signature = request.query_params.get("user_signature")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Get user's sources
    sources_result = await db.execute(
        select(Source).where(Source.user_id == user_id)
    )
    sources = sources_result.scalars().all()

    stats = []
    for source in sources:
        # Count items parsed
        items_result = await db.execute(
            select(func.count(SourceItem.id)).where(SourceItem.source_id == source.id)
        )
        items_parsed = items_result.scalar() or 0

        # Count posts created from this source
        posts_result = await db.execute(
            select(func.count(Post.id)).where(
                Post.user_id == user_id,
                Post.source_item_id.in_(
                    select(SourceItem.id).where(SourceItem.source_id == source.id)
                )
            )
        )
        posts_created = posts_result.scalar() or 0

        stats.append({
            "source_id": source.id,
            "source_name": source.name,
            "items_parsed": items_parsed,
            "posts_created": posts_created,
        })

    return stats
