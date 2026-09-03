from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.user import User
from api.dependencies import get_current_user

router = APIRouter()


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    class Config:
        from_attributes = True


@router.post("/")
async def create_or_get_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create user if doesn't exist, or return existing."""
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

    telegram_id = body.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id required")

    # Check if user exists
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return UserResponse.from_orm(existing_user)

    # Create new user
    try:
        new_user = User(
            id=telegram_id,  # Use telegram_id as primary key for simplicity
            telegram_id=telegram_id,
            username=body.get("username"),
            first_name=body.get("first_name"),
            last_name=body.get("last_name"),
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return UserResponse.from_orm(new_user)
    except IntegrityError:
        await db.rollback()
        # User might have been created by another request
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return UserResponse.from_orm(existing_user)
        raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user by telegram_id."""
    if user_id != current_user.telegram_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = await db.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.from_orm(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user by telegram_id."""
    if user_id != current_user.telegram_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Find and update user
    result = await db.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Whitelist allowed fields, never allow user to set their own admin status
    allowed_fields = {"username", "first_name", "last_name"}
    if current_user.is_admin:
        allowed_fields.update({"is_approved", "is_admin"})

    for field in allowed_fields:
        if field in body:
            setattr(user, field, body[field])

    try:
        db.add(user)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    await db.refresh(user)

    return UserResponse.from_orm(user)
