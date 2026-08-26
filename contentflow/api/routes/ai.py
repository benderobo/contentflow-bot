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


@router.get("/stats")
async def get_ai_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get AI usage statistics summary for a user."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")

    result = await db.execute(
        select(AIRequest).where(AIRequest.user_id == user_id).order_by(AIRequest.created_at.desc())
    )
    requests = result.scalars().all()

    total_tokens = sum(r.tokens_used or 0 for r in requests)
    estimated_cost = total_tokens * 0.000002  # Approximate cost per token

    return {
        "texts_processed": len(requests),
        "tokens_used": total_tokens,
        "estimated_cost": f"{estimated_cost:.2f}",
        "provider": settings.ai_provider,
        "last_used": requests[0].created_at.isoformat() if requests else "Never"
    }


@router.get("/usage")
async def get_ai_usage(user_id: int, period: str = "today", db: AsyncSession = Depends(get_db)):
    """Get AI usage statistics for a period."""
    from datetime import datetime, timedelta

    query = select(AIUsage).where(AIUsage.user_id == user_id)

    if period == "today":
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.where(AIUsage.date >= start)
    elif period == "week":
        start = datetime.utcnow() - timedelta(days=7)
        query = query.where(AIUsage.date >= start)
    elif period == "month":
        start = datetime.utcnow() - timedelta(days=30)
        query = query.where(AIUsage.date >= start)

    result = await db.execute(query.order_by(AIUsage.date.desc()).limit(100))
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
async def analyze_content(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Analyze content using AI."""
    from api.dependencies import verify_user_id_signature

    user_id = await verify_user_id_signature(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    text = body.get("text")
    if not text or len(text) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters")

    try:
        ai_service = get_ai_provider()
        analysis = await ai_service.analyze_content(text)

        ai_request = AIRequest(
            user_id=user_id,
            endpoint="/analyze",
            input_text=text[:1000],
            output_text=str(analysis)[:1000],
            model=settings.ai_model,
            tokens_used=0
        )
        db.add(ai_request)
        await db.commit()

        return analysis
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
async def rewrite_content(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Rewrite content using AI."""
    from api.dependencies import verify_user_id_signature

    user_id = await verify_user_id_signature(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    text = body.get("text")
    style = body.get("style", "neutral")

    if not text or len(text) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters")

    if style not in ["neutral", "engaging", "informative", "professional"]:
        raise HTTPException(status_code=400, detail="Invalid style. Must be one of: neutral, engaging, informative, professional")

    try:
        ai_service = get_ai_provider()
        rewritten = await ai_service.rewrite_content(text, style=style)

        ai_request = AIRequest(
            user_id=user_id,
            endpoint="/rewrite",
            input_text=text[:1000],
            output_text=rewritten[:1000],
            model=settings.ai_model,
            tokens_used=0
        )
        db.add(ai_request)
        await db.commit()

        return {"original": text, "rewritten": rewritten, "style": style}
    except Exception as e:
        logger.error(f"Rewrite error: {e}")
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")
