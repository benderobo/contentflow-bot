from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db
from core.config import get_settings
from models.ai_usage import AIUsage
from models.ai_request import AIRequest
from models.post import Post
from api.dependencies import verify_service_auth
from services.ai import AIService, OpenAIProvider, AnthropicProvider, OllamaProvider

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


@router.get("/usage")
async def get_ai_usage(user_id: int, period: str = "today", db: AsyncSession = Depends(get_db)):
    """Get AI usage statistics for a period."""
    # TODO: Implement period filtering
    result = await db.execute(
        select(AIUsage)
        .where(AIUsage.user_id == user_id)
        .order_by(AIUsage.date.desc())
        .limit(30)
    )
    usage = result.scalars().all()
    return [AIUsageResponse.from_orm(u) for u in usage]


@router.get("/requests")
async def get_ai_requests(user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent AI requests."""
    result = await db.execute(
        select(AIRequest)
        .where(AIRequest.user_id == user_id)
        .order_by(AIRequest.created_at.desc())
        .limit(limit)
    )
    requests = result.scalars().all()
    return requests


@router.post("/analyze")
async def analyze_content(user_id: int, text: str, db: AsyncSession = Depends(get_db)):
    """Analyze content using AI."""
    # TODO: Queue AI analysis task
    return {"message": "Analysis queued"}


def get_ai_provider() -> AIService:
    """Initialize AI provider based on configuration."""
    if settings.ai_provider == "openai":
        provider = OpenAIProvider(settings.openai_api_key, settings.ai_model)
    elif settings.ai_provider == "anthropic":
        provider = AnthropicProvider(settings.anthropic_api_key, settings.ai_model)
    elif settings.ai_provider == "ollama":
        provider = OllamaProvider(settings.ollama_url, settings.ai_model)
    else:
        # Default to OpenAI, but will fail if no key
        provider = OpenAIProvider(settings.openai_api_key, settings.ai_model)

    return AIService(provider)


class RewritePostRequest(BaseModel):
    style: str = "neutral"
    user_id: int


@router.post("/posts/{post_id}/rewrite")
async def rewrite_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Rewrite a post using AI."""
    from utils.auth import verify_user_id

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    user_id = body.get("user_id")
    user_signature = body.get("user_signature")
    style = body.get("style", "neutral")

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
    _: bool = Depends(verify_service_auth),
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
async def rewrite_content(user_id: int, text: str, style: str = "neutral", db: AsyncSession = Depends(get_db)):
    """Rewrite content using AI."""
    # TODO: Queue AI rewrite task
    return {"message": "Rewrite queued"}
