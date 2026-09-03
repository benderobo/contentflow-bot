from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db
from models.post import Post
from models.publish_job import PublishJob
from models.user import User
from api.dependencies import get_current_user
from models.channel import Channel
from api.dependencies import verify_service_auth

router = APIRouter()


class PostCreate(BaseModel):
    source_item_id: Optional[int] = None
    title: str
    body: str
    hashtags: list = []

    class Config:
        extra = "forbid"  # Reject unknown fields


class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    hashtags: Optional[list] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PostResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    body: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
async def list_posts(
    request: Request,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """List posts for current user."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")

    query = select(Post).where(Post.user_id == user_id)
    if status:
        query = query.where(Post.status == status)
    query = query.order_by(Post.created_at.desc())

    result = await db.execute(query)
    posts = result.scalars().all()
    return [PostResponse.from_orm(p) for p in posts]


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return PostResponse.from_orm(post)


@router.post("/")
async def create_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new post (supports both WebApp auth and service auth)."""
    from utils.auth import verify_user_id
    from utils.webapp_auth import verify_webapp_init_data
    from core.config import get_settings

    user_id = None

    # Try WebApp initData auth first (for miniapp)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("tg-init-data "):
        init_data = auth_header.replace("tg-init-data ", "", 1)
        settings = get_settings()
        user_data = verify_webapp_init_data(init_data, settings.bot_token)
        if user_data and "user" in user_data:
            user_id = user_data["user"].get("id")

    # Fall back to service auth (for bot handlers)
    if not user_id:
        try:
            await verify_service_auth(request)
        except HTTPException:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")

        user_id = body.get("user_id")
        user_signature = body.get("user_signature")

        if not user_id or not user_signature:
            raise HTTPException(status_code=400, detail="user_id and user_signature required")

        if not verify_user_id(int(user_id), user_signature):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Validate through Pydantic model, exclude user_id, user_signature, media, status
    try:
        post_input = PostCreate(**{k: v for k, v in body.items()
                                   if k not in ["user_id", "user_signature", "media", "status"]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract status if provided (defaults to 'draft')
    post_status = body.get("status", "draft")

    db_post = Post(**post_input.dict(), user_id=user_id, status=post_status)
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return PostResponse.from_orm(db_post)


@router.patch("/{post_id}")
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    update_data = post_update.dict(exclude_unset=True)
    # Whitelist editable fields
    allowed_fields = {"title", "body", "hashtags", "status", "scheduled_at"}
    for field in list(update_data.keys()):
        if field not in allowed_fields:
            del update_data[field]

    for field, value in update_data.items():
        setattr(post, field, value)

    db.add(post)
    await db.commit()
    await db.refresh(post)
    return PostResponse.from_orm(post)


class RewriteRequest(BaseModel):
    style: str = "neutral"


@router.post("/{post_id}/rewrite")
async def rewrite_post(
    post_id: int,
    request: RewriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rewrite a post using AI."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Get AI service
    from services.ai import AIService, OpenAIProvider, MockProvider
    from core.config import get_settings

    settings = get_settings()

    # Choose AI provider based on configuration
    if settings.openai_api_key:
        provider = OpenAIProvider(settings.openai_api_key, settings.ai_model)
    else:
        provider = MockProvider()

    ai_service = AIService(provider)

    # Rewrite content
    text_to_rewrite = post.body or post.title or ""
    try:
        rewritten = await ai_service.rewrite_content(text_to_rewrite, style=request.style)

        # Save rewritten content
        post.rewrite_candidate = rewritten
        db.add(post)
        await db.commit()

        return {
            "message": "Post rewritten successfully",
            "post_id": post_id,
            "rewritten_content": rewritten,
            "style": request.style
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")


@router.post("/{post_id}/use-rewrite")
async def use_rewrite(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply rewritten content to post body."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Check if rewritten content exists
    if not post.rewrite_candidate:
        raise HTTPException(status_code=400, detail="No rewritten content available")

    # Save original as rewrite_original for reference, apply candidate as body
    post.rewrite_original = post.body
    post.body = post.rewrite_candidate
    post.rewrite_candidate = None  # Clear candidate after use
    db.add(post)
    await db.commit()

    return {
        "message": "Rewritten content applied",
        "post_id": post_id,
        "new_body": post.body
    }


@router.post("/{post_id}/approve")
async def approve_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    post.status = "approved"
    db.add(post)
    await db.commit()
    return {"message": "Post approved"}


class PublishPostRequest(BaseModel):
    channel_id: int


@router.post("/{post_id}/publish")
async def publish_post(
    post_id: int,
    request: PublishPostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a post to Telegram channel."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Verify channel exists and belongs to user
    channel_result = await db.execute(
        select(Channel).where(Channel.id == request.channel_id, Channel.user_id == current_user.id)
    )
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Queue publish task
    from workers.tasks import publish_post as publish_task
    publish_task.delay(post_id, request.channel_id)

    return {"message": "Post queued for publishing", "post_id": post_id, "channel_id": request.channel_id}


# ===== PUBLISH SCHEDULING ENDPOINTS =====

class PublishScheduleRequest(BaseModel):
    post_id: int
    channel_id: int
    scheduled_at: Optional[str] = None
    user_id: int


@router.post("/publish/now")
async def publish_now(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Publish post immediately."""
    from utils.auth import verify_user_id

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    user_id = body.get("user_id")
    user_signature = body.get("user_signature")
    post_id = body.get("post_id")
    channel_id = body.get("channel_id")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Verify post ownership
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post or post.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Verify channel ownership
    channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel or channel.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Publish immediately
    post.status = "published"
    post.published_at = datetime.utcnow()
    db.add(post)

    # Create publish job with immediate timestamp
    job = PublishJob(
        post_id=post_id,
        channel_id=channel_id,
        scheduled_at=datetime.utcnow(),
        status="published",
        published_at=datetime.utcnow(),
    )
    db.add(job)
    await db.commit()

    return {"message": "Post published", "post_id": post_id, "channel_id": channel_id}


@router.post("/publish/schedule")
async def schedule_publish(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Schedule post for later publishing."""
    from utils.auth import verify_user_id

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    user_id = body.get("user_id")
    user_signature = body.get("user_signature")
    post_id = body.get("post_id")
    channel_id = body.get("channel_id")
    scheduled_at_str = body.get("scheduled_at")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Parse scheduled_at
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid scheduled_at format (use ISO format)")

    # Verify post ownership
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post or post.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Verify channel ownership
    channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel or channel.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Create publish job
    job = PublishJob(
        post_id=post_id,
        channel_id=channel_id,
        scheduled_at=scheduled_at,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return {
        "message": "Post scheduled",
        "job_id": job.id,
        "scheduled_at": scheduled_at.isoformat(),
    }


@router.get("/publish/scheduled")
async def get_scheduled_posts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get scheduled posts for user."""
    from utils.auth import verify_user_id

    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    user_signature = request.query_params.get("user_signature")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Get user's channels
    channels_result = await db.execute(
        select(Channel).where(Channel.user_id == user_id)
    )
    user_channels = {ch.id for ch in channels_result.scalars().all()}

    # Get pending jobs for user's channels
    jobs_result = await db.execute(
        select(PublishJob).where(
            PublishJob.channel_id.in_(user_channels),
            PublishJob.status == "pending"
        ).order_by(PublishJob.scheduled_at.asc())
    )
    jobs = jobs_result.scalars().all()

    result = []
    for job in jobs:
        post_result = await db.execute(select(Post).where(Post.id == job.post_id))
        post = post_result.scalar_one_or_none()

        channel_result = await db.execute(select(Channel).where(Channel.id == job.channel_id))
        channel = channel_result.scalar_one_or_none()

        result.append({
            "id": job.id,
            "post_id": job.post_id,
            "post_title": post.title if post else "Unknown",
            "channel_id": job.channel_id,
            "channel_name": channel.name if channel else "Unknown",
            "scheduled_at": job.scheduled_at.isoformat(),
            "status": job.status,
        })

    return result


@router.post("/publish/{job_id}/cancel")
async def cancel_publish_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Cancel scheduled publish job."""
    from utils.auth import verify_user_id

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    user_id = body.get("user_id")
    user_signature = body.get("user_signature")

    if not user_id or not user_signature:
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(user_id), user_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Get job
    job_result = await db.execute(select(PublishJob).where(PublishJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership through channel
    channel_result = await db.execute(select(Channel).where(Channel.id == job.channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel or channel.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Cancel job
    job.status = "cancelled"
    db.add(job)
    await db.commit()

    return {"message": "Job cancelled", "job_id": job_id}
