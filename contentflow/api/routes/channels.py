from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.channel import Channel
from models.user import User
from api.dependencies import get_current_user

router = APIRouter()


class ChannelCreate(BaseModel):
    name: str
    telegram_id: str
    username: Optional[str] = None
    bot_token: Optional[str] = None
    enabled: bool = True


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List channels for current user."""
    result = await db.execute(
        select(Channel).where(Channel.user_id == current_user.id).order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return [ChannelResponse.from_orm(c) for c in channels]


@router.post("/")
async def create_channel(
    channel: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new channel."""
    db_channel = Channel(**channel.dict(), user_id=current_user.id)
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)
    return ChannelResponse.from_orm(db_channel)


@router.get("/{channel_id}")
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return ChannelResponse.from_orm(channel)


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: int,
    updates: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Only update whitelisted fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.add(channel)
    await db.commit()
    return ChannelResponse.from_orm(channel)
