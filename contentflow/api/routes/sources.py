from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.source import Source
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SourceCreate(BaseModel):
    user_id: int
    name: str
    type: str
    url: Optional[str] = None
    enabled: bool = True
    parse_interval: int = 3600
    parser_config: dict = {}
    filters: dict = {}


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
async def list_sources(user_id: int, db: AsyncSession = Depends(get_db)):
    """List all sources for a user."""
    result = await db.execute(
        select(Source).where(Source.user_id == user_id).order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()
    return [SourceResponse.from_orm(s) for s in sources]


@router.get("/{source_id}")
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.from_orm(source)


@router.post("/")
async def create_source(source: SourceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new source."""
    db_source = Source(**source.dict())
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)
    return SourceResponse.from_orm(db_source)


@router.patch("/{source_id}")
async def update_source(
    source_id: int, source_update: SourceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = source_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceResponse.from_orm(source)


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()
    return {"message": "Source deleted"}
