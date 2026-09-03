import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db
from models.user import User
from core.config import get_settings
from models.ai_usage import AIUsage
from models.ai_request import AIRequest
from models.post import Post
from api.dependencies import get_current_user
from services.ai import AIService, OpenAIProvider, AnthropicProvider, OllamaProvider, MockProvider

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class AIUsageResponse(BaseModel):
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float

    class Config:
        from_attributes = True


@router.get("/stats")
async def get_ai_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI usage statistics summary for a user."""
    user_id = current_user.id

    # Get post
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        ai_service = get_ai_provider()
        rewritten = await ai_service.rewrite_content(post.body, style=style)

        # Store original for comparison
        post.rewrite_original = post.body
        post.rewrite_candidate = rewritten
        db.add(post)
        await db.commit()

        return {
            "id": post.id,
            "original_content": post.body,
            "rewritten_content": rewritten,
            "style": style
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


@router.post("/posts/{post_id}/use-rewrite")
async def use_rewrite_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply rewritten content to a post."""
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

    # Get post
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != int(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if not post.rewrite_candidate:
        raise HTTPException(status_code=400, detail="No rewritten content available")

    # Apply rewrite
    post.body = post.rewrite_candidate
    post.rewrite_candidate = None
    post.rewrite_original = None
    post.updated_at = datetime.utcnow()
    db.add(post)
    await db.commit()

    return {"message": "Rewritten content applied", "post_id": post.id}


@router.post("/rewrite")
async def rewrite_content(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Rewrite content using AI (supports bot API and WebApp auth)."""
    from api.dependencies import verify_user_id_signature
    from utils.webapp_auth import verify_webapp_init_data

    user_id = None

    # Try WebApp initData auth first (for miniapp)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("tg-init-data "):
        init_data = auth_header.replace("tg-init-data ", "", 1)
        user_data = verify_webapp_init_data(init_data, settings.bot_token)
        if user_data and "user" in user_data:
            user_id = user_data["user"].get("id")

    # Fall back to service auth (for bot handlers)
    if not user_id:
        try:
            await verify_service_auth(request)
            user_id = await verify_user_id_signature(request)
        except HTTPException:
            raise HTTPException(status_code=401, detail="Unauthorized")

    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    text = body.get("text")
    style = body.get("style", "neutral")
    replace_from = body.get("replace_from")
    replace_to = body.get("replace_to")

    if not text or len(text) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters")

    if style not in ["neutral", "engaging", "informative", "professional"]:
        raise HTTPException(status_code=400, detail="Invalid style. Must be one of: neutral, engaging, informative, professional")

    try:
        ai_service = get_ai_provider()
        rewritten = await ai_service.rewrite_content(
            text,
            style=style,
            replace_from=replace_from,
            replace_to=replace_to
        )

        ai_request = AIRequest(
            user_id=user_id,
            request_type="rewrite",
            input_text=text[:1000],
            output_text=rewritten[:1000],
            model=settings.ai_model,
            total_tokens=0,
            status="completed"
        )
        db.add(ai_request)
        await db.commit()

        return {"original": text, "rewritten": rewritten, "style": style}
    except Exception as e:
        logger.error(f"Rewrite error: {e}")
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")
