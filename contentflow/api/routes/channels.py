from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.channel import Channel

router = APIRouter()


class ChannelCreate(BaseModel):
    user_id: int
    name: str
    telegram_id: str
    username: Optional[str] = None
    bot_token: Optional[str] = None
    enabled: bool = True


class ChannelResponse(BaseModel):
    id: int
    user_id: int
    name: str
    telegram_id: str
    enabled: bool

    class Config:
        from_attributes = True


@router.get("/")
async def list_channels(user_id: int, db: AsyncSession = Depends(get_db)):
    """List channels for a user."""
    result = await db.execute(
        select(Channel).where(Channel.user_id == user_id).order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return [ChannelResponse.from_orm(c) for c in channels]


@router.post("/")
async def create_channel(channel: ChannelCreate, db: AsyncSession = Depends(get_db)):
    """Create a new channel."""
    db_channel = Channel(**channel.dict())
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)
    return ChannelResponse.from_orm(db_channel)


@router.get("/{channel_id}")
async def get_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse.from_orm(channel)


@router.patch("/{channel_id}")
async def update_channel(channel_id: int, updates: dict, db: AsyncSession = Depends(get_db)):
    """Update a channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for field, value in updates.items():
        if hasattr(channel, field):
            setattr(channel, field, value)

    db.add(channel)
    await db.commit()
    return ChannelResponse.from_orm(channel)
