from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db
from models.post import Post
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
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List posts for current user."""
    query = select(Post).where(Post.user_id == current_user.id)
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
    _: bool = Depends(verify_service_auth),
):
    """Create a new post."""
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

    # Validate through Pydantic model, exclude user_id and signature
    try:
        post_input = PostCreate(**{k: v for k, v in body.items()
                                   if k not in ["user_id", "user_signature"]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_post = Post(**post_input.dict(), user_id=user_id)
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


@router.post("/{post_id}/rewrite")
async def rewrite_post(
    post_id: int,
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

    # TODO: Implement AI rewrite
    return {"message": "Rewrite queued"}


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


@router.post("/{post_id}/publish")
async def publish_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    post.status = "published"
    post.published_at = datetime.utcnow()
    db.add(post)
    await db.commit()
    return {"message": "Post published"}
