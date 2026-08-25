from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from models.source import Source
from models.source_item import SourceItem
from pydantic import BaseModel
from api.dependencies import verify_service_auth

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
    _: bool = Depends(verify_service_auth),
):
    """List all sources for a user."""
    # Get user_id from query params
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")

    result = await db.execute(
        select(Source).where(Source.user_id == user_id).order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()
    return [SourceResponse.from_orm(s) for s in sources]


@router.get("/{source_id}")
async def get_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Get a specific source."""
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
    return SourceResponse.from_orm(source)


@router.post("/")
async def create_source(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_service_auth),
):
    """Create a new source."""
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
    _: bool = Depends(verify_service_auth),
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
    _: bool = Depends(verify_service_auth),
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
    _: bool = Depends(verify_service_auth),
):
    """Get unanalyzed source items for a user."""
    user_id_str = request.query_params.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="user_id required")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    limit_str = request.query_params.get("limit", "5")
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 5

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

    # Get unanalyzed items from user's sources
    result = await db.execute(
        select(SourceItem).where(
            SourceItem.source_id.in_(source_ids),
            SourceItem.ai_analysis == None
        ).order_by(SourceItem.created_at.desc()).limit(limit)
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
