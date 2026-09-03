from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.channel import Channel
from models.user import User
from api.dependencies import verify_service_auth
from utils.auth import verify_user_id

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
    enabled: Optional[bool] = True

    class Config:
        from_attributes = True


@router.get("/", name="list_channels_slash")
@router.get("", name="list_channels_no_slash")
async def list_channels(
    request: Request,
    user_id: int,
    user_signature: str,
    db: AsyncSession = Depends(get_db),
):
    """List channels for user with service auth."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await verify_service_auth(request)

    if not verify_user_id(user_id, user_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    result = await db.execute(
        select(Channel).where(Channel.user_id == user_id).order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return [ChannelResponse.from_orm(c) for c in channels]


@router.post("/")
async def create_channel(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new channel with service auth."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await verify_service_auth(request)

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
    user_id: int,
    user_signature: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a channel by ID with service auth."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await verify_service_auth(request)

    if not verify_user_id(user_id, user_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ChannelResponse.from_orm(channel)


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    request: Request,
    user_id: int,
    user_signature: str,
    db: AsyncSession = Depends(get_db),
):
    """Update a channel with service auth."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await verify_service_auth(request)

    if not verify_user_id(user_id, user_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = channel_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ChannelResponse.from_orm(channel)
