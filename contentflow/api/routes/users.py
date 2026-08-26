from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from models.user import User
from api.dependencies import verify_service_auth

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
    _: bool = Depends(verify_service_auth),
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get user by telegram_id."""
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
    _: bool = Depends(verify_service_auth),
):
    """Update user by telegram_id."""
    import logging
    from utils.auth import verify_user_id

    logger = logging.getLogger(__name__)

    try:
        body = await request.json()
        safe_body = {k: v for k, v in body.items() if k != "user_signature"}
        logger.info(f"PATCH /api/users/{user_id} body: {safe_body}")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

    caller_user_id = body.get("user_id")
    user_signature = body.get("user_signature")

    logger.info(f"Caller user_id: {caller_user_id}")

    if not caller_user_id or not user_signature:
        logger.error(f"Missing user_id or user_signature")
        raise HTTPException(status_code=400, detail="user_id and user_signature required")

    if not verify_user_id(int(caller_user_id), user_signature):
        logger.error(f"Invalid signature for user {caller_user_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user signature")

    # Only admins can update users
    caller_result = await db.execute(select(User).where(User.telegram_id == int(caller_user_id)))
    caller = caller_result.scalar_one_or_none()
    logger.info(f"Caller: {caller}, is_admin: {caller.is_admin if caller else None}")
    if not caller or not caller.is_admin:
        logger.error(f"Caller {caller_user_id} is not admin")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update users")

    # Find and update user
    result = await db.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    logger.info(f"Updating user {user_id}: {user}")

    if not user:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if "is_approved" in body:
        user.is_approved = body.get("is_approved")
        logger.info(f"Setting is_approved to {user.is_approved}")
    if "is_admin" in body:
        user.is_admin = body.get("is_admin")
    if "username" in body:
        user.username = body.get("username")
    if "first_name" in body:
        user.first_name = body.get("first_name")

    try:
        db.add(user)
        await db.commit()
        logger.info(f"User {user_id} updated successfully")
    except Exception as e:
        logger.error(f"Database error updating user: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    await db.refresh(user)

    return UserResponse.from_orm(user)
