from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.channel import Channel
from models.user import User
from api.dependencies import verify_service_auth, get_current_user

router = APIRouter()


class ChannelCreate(BaseModel):
    name: str
    telegram_id: str
    username: Optional[str] = None
    bot_token: Optional[str] = None
    enabled: bool = True

    class Config:
        extra = "forbid"  # Reject unknown fields


class ChannelUpdate(BaseModel):
    """Whitelist only user-editable fields."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    username: Optional[str] = None


class ChannelResponse(BaseModel):
    id: int
    user_id: int
    name: str
    telegram_id: str
    enabled: bool

    class Config:
        from_attributes = True


@router.get("/")
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List channels for current user."""
    result = await db.execute(
        select(Channel).where(Channel.user_id == current_user.id).order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return [ChannelResponse.from_orm(c) for c in channels]


@router.post("/")
async def create_channel(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Create a new channel."""
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

    # Validate through Pydantic model
    try:
        channel_input = ChannelCreate(**{k: v for k, v in body.items() if k not in ["user_id", "user_signature"]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_channel = Channel(**channel_input.dict(), user_id=user_id)
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)
    return ChannelResponse.from_orm(db_channel)


@router.get("/{channel_id}")
async def get_channel(
    channel_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get a specific channel."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return ChannelResponse.from_orm(channel)


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: int,
    updates: ChannelUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Update a channel."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Only update whitelisted fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.add(channel)
    await db.commit()
    return ChannelResponse.from_orm(channel)
