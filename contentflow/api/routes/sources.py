from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from models.user import User
from models.source import Source
from models.source_item import SourceItem
from pydantic import BaseModel
from api.dependencies import get_current_user, verify_service_auth

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    type: str
    url: Optional[str] = None
    enabled: bool = True
    parse_interval: int = 3600
    parser_config: dict = {}
    filters: dict = {}

    class Config:
        extra = "forbid"  # Reject unknown fields


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    parse_interval: Optional[int] = None
    parser_config: Optional[dict] = None
    filters: Optional[dict] = None


class SourceResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    url: Optional[str]
    enabled: bool
    parse_interval: int

    class Config:
        from_attributes = True


@router.get("/")
async def list_sources(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sources for a user."""
    # Get user_id from query params
    user_id = current_user.id

    # Validate through Pydantic model
    try:
        source_input = SourceCreate(**{k: v for k, v in body.items() if k not in ["user_id", "user_signature"]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_source = Source(**source_input.dict(), user_id=user_id)
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)
    return SourceResponse.from_orm(db_source)


@router.patch("/{source_id}")
async def update_source(
    source_id: int,
    source_update: SourceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a source."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    update_data = source_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceResponse.from_orm(source)


@router.delete("/{source_id}")
async def delete_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a source."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    await db.delete(source)
    await db.commit()
    return {"message": "Source deleted"}


@router.get("/items/unanalyzed")
async def get_unanalyzed_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get unanalyzed source items for a user."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    limit_str = request.query_params.get("limit", "10")
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 10

    source_id_str = request.query_params.get("source_id")
    source_id = None
    if source_id_str:
        try:
            source_id = int(source_id_str)
        except ValueError:
            pass

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # Get sources for user
    sources_result = await db.execute(
        select(Source).where(Source.user_id == user_id)
    )
    sources = sources_result.scalars().all()
    source_ids = [s.id for s in sources]

    if not source_ids:
        return []

    # Filter by source_id if provided
    if source_id and source_id not in source_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    query = select(SourceItem).where(SourceItem.ai_analysis == None)

    if source_id:
        query = query.where(SourceItem.source_id == source_id)
    else:
        query = query.where(SourceItem.source_id.in_(source_ids))

    result = await db.execute(
        query.order_by(SourceItem.created_at.desc()).limit(limit)
    )
    items = result.scalars().all()

    return [
        {
            "id": item.id,
            "title": item.title,
            "description": item.description[:200] if item.description else "",
            "source_id": item.source_id,
        }
        for item in items
    ]


@router.get("/items/{item_id}")
async def get_source_item(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific source item for editing in miniapp (WebApp auth)."""
    from utils.webapp_auth import verify_webapp_init_data
    from core.config import get_settings

    settings = get_settings()

    # Extract and validate Telegram WebApp initData
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("tg-init-data "):
        raise HTTPException(status_code=401, detail="Missing or invalid auth header")

    init_data = auth_header.replace("tg-init-data ", "", 1)
    user_data = verify_webapp_init_data(init_data, settings.bot_token)

    if not user_data or "user" not in user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired initData")

    user_id = user_data["user"].get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in initData")

    result = await db.execute(
        select(SourceItem).where(SourceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify user owns the source
    source_result = await db.execute(
        select(Source).where(Source.id == item.source_id)
    )
    source = source_result.scalar_one_or_none()

    if not source or source.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": item.id,
        "title": item.title,
        "description": item.description or "",
        "content": item.content or "",
        "source_id": item.source_id,
        "original_url": item.original_url,
        "author": item.author,
    }


@router.post("/parse-all")
async def parse_all_sources(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Parse all enabled sources for a user."""
    from services.parser import ParserFactory
    from utils.auth import verify_user_id
    import logging

    logger = logging.getLogger(__name__)

    # Handle both JWT and service auth
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Try JWT first
        current_user = await get_current_user(request, db)
        user_id = current_user.id
    except HTTPException:
        # If JWT fails, try service auth with signature
        await verify_service_auth(request)

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")

        user_id_str = body.get("user_id")
        user_signature = body.get("user_signature")

        if not user_id_str or not user_signature:
            raise HTTPException(status_code=400, detail="user_id and user_signature required for service auth")

        try:
            user_id = int(user_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be an integer")

        if not verify_user_id(user_id, user_signature):
            raise HTTPException(status_code=403, detail="Invalid user signature")

    result = await db.execute(
        select(Source).where(Source.user_id == user_id, Source.enabled == True)
    )
    sources = result.scalars().all()

    parsed_count = 0
    items_count = 0

    for source in sources:
        try:
            parser = ParserFactory.get_parser(source.type)
            if not parser:
                logger.warning(f"Unknown parser type: {source.type}")
                continue

            config = source.parser_config or {}
            config["url"] = source.url
            config["username"] = source.url  # For Telegram
            logger.debug(f"Parsing source {source.id} ({source.type}) with config: {config}")

            items = await parser.parse(config)

            if items:
                items_count += len(items)
                parsed_count += 1

                new_items = 0
                skipped_items = 0

                for item in items:
                    import hashlib
                    content = item.get("content", "") or item.get("description", "")
                    content_hash = hashlib.sha256(content.encode()).hexdigest() if content else None
                    original_url = item.get("url", "")

                    # Check if item already exists
                    existing = await db.execute(
                        select(SourceItem).where(SourceItem.original_url == original_url)
                    )
                    if existing.scalar_one_or_none():
                        skipped_items += 1
                        continue

                    db_item = SourceItem(
                        source_id=source.id,
                        original_url=original_url,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        content=content,
                        author=item.get("author"),
                        published_at=item.get("published_at"),
                        content_hash=content_hash,
                    )
                    db.add(db_item)
                    new_items += 1

                if new_items > 0:
                    await db.commit()
                    logger.info(f"Source {source.id}: Added {new_items} new items, skipped {skipped_items} duplicates")
        except Exception as e:
            logger.error(f"Error parsing source {source.id}: {e}")
            continue

    return {
        "parsed_count": parsed_count,
        "items_count": items_count,
        "message": f"Parsed {parsed_count} sources, got {items_count} items"
    }
