from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import os
import hmac
import logging

from core.config import get_settings
from core.database import get_db
from models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()
API_KEY = os.environ["API_KEY"]  # Fail hard if not set


async def verify_service_auth(request: Request) -> bool:
    """Verify service-level authentication from Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.error(f"Missing/invalid Bearer token in Authorization header. Got: {auth_header[:50] if auth_header else 'EMPTY'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(token, API_KEY):
        logger.error(f"Invalid API key. Expected: {API_KEY[:20]}..., Got: {token[:20]}...")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return True


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT token in Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user


async def verify_user_id_signature(request: Request) -> int:
    """Verify user_id and its HMAC signature from request body."""
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

    return int(user_id)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return current_user
