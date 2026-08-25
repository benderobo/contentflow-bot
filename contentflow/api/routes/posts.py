from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db
from models.post import Post

router = APIRouter()


class PostCreate(BaseModel):
    user_id: int
    source_item_id: Optional[int] = None
    title: str
    body: str
    hashtags: list = []


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
async def list_posts(user_id: int, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List posts for a user."""
    query = select(Post).where(Post.user_id == user_id)
    if status:
        query = query.where(Post.status == status)
    query = query.order_by(Post.created_at.desc())

    result = await db.execute(query)
    posts = result.scalars().all()
    return [PostResponse.from_orm(p) for p in posts]


@router.get("/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.from_orm(post)


@router.post("/")
async def create_post(post: PostCreate, db: AsyncSession = Depends(get_db)):
    """Create a new post."""
    db_post = Post(**post.dict())
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return PostResponse.from_orm(db_post)


@router.patch("/{post_id}")
async def update_post(
    post_id: int, post_update: PostUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    update_data = post_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    db.add(post)
    await db.commit()
    await db.refresh(post)
    return PostResponse.from_orm(post)


@router.post("/{post_id}/rewrite")
async def rewrite_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Rewrite a post using AI."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # TODO: Implement AI rewrite
    return {"message": "Rewrite queued"}


@router.post("/{post_id}/approve")
async def approve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "approved"
    db.add(post)
    await db.commit()
    return {"message": "Post approved"}


@router.post("/{post_id}/publish")
async def publish_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Publish a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "published"
    post.published_at = datetime.utcnow()
    db.add(post)
    await db.commit()
    return {"message": "Post published"}
