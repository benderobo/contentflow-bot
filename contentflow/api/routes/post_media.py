import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.dependencies import get_current_user_webapp_or_jwt
from core.config import get_settings
from core.database import get_db
from models.post import Post
from models.post_media import PostMedia
from models.user import User
from utils.media import (
    MAX_IMAGE_SIZE,
    MAX_IMAGES_PER_POST,
    detect_image_type,
    file_sha256,
    new_media_relpath,
    resolve_media_path,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


def _serialize(media: PostMedia) -> dict:
    return {
        "id": media.id,
        "post_id": media.post_id,
        "media_type": media.media_type,
        "mime_type": media.mime_type,
        "file_size": media.file_size,
        "order": media.order,
        "url": f"/api/posts/{media.post_id}/media/{media.id}/file",
    }


async def _get_owned_post(post_id: int, user: User, db: AsyncSession) -> Post:
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return post


async def _get_media(post_id: int, media_id: int, db: AsyncSession) -> PostMedia:
    result = await db.execute(
        select(PostMedia).where(PostMedia.id == media_id, PostMedia.post_id == post_id)
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


@router.get("/{post_id}/media")
async def list_media(
    post_id: int,
    current_user: User = Depends(get_current_user_webapp_or_jwt),
    db: AsyncSession = Depends(get_db),
):
    """List images attached to a post."""
    await _get_owned_post(post_id, current_user, db)
    result = await db.execute(
        select(PostMedia).where(PostMedia.post_id == post_id).order_by(PostMedia.order, PostMedia.id)
    )
    return [_serialize(m) for m in result.scalars().all()]


@router.post("/{post_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    post_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_webapp_or_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Attach an image (JPEG/PNG/WEBP, up to 10 MB) to a post."""
    post = await _get_owned_post(post_id, current_user, db)
    if post.status == "published":
        raise HTTPException(status_code=409, detail="Cannot change media of a published post")

    count = (
        await db.execute(select(func.count()).select_from(PostMedia).where(PostMedia.post_id == post_id))
    ).scalar_one()
    if count >= MAX_IMAGES_PER_POST:
        raise HTTPException(status_code=400, detail=f"At most {MAX_IMAGES_PER_POST} images per post")

    # Read one byte past the limit so oversize uploads are detected without buffering them fully.
    data = await file.read(MAX_IMAGE_SIZE + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image is larger than 10 MB")

    detected = detect_image_type(data)
    if not detected:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WEBP images are supported")
    ext, mime = detected

    digest = file_sha256(data)
    duplicate = await db.execute(
        select(PostMedia.id).where(PostMedia.post_id == post_id, PostMedia.file_hash == digest)
    )
    if duplicate.first():
        raise HTTPException(status_code=409, detail="This image is already attached")

    relpath = new_media_relpath(post_id, ext)
    full_path = resolve_media_path(settings.media_storage_path, relpath)

    def _write() -> None:
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_bytes(data)

    await run_in_threadpool(_write)

    media = PostMedia(
        post_id=post_id,
        media_type="image",
        file_path=relpath,
        file_size=len(data),
        file_hash=digest,
        mime_type=mime,
        order=count,
    )
    db.add(media)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await run_in_threadpool(lambda: full_path.unlink(missing_ok=True))
        raise
    await db.refresh(media)
    return _serialize(media)


@router.get("/{post_id}/media/{media_id}/file")
async def get_media_file(
    post_id: int,
    media_id: int,
    current_user: User = Depends(get_current_user_webapp_or_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Download an attached image (authenticated; the miniapp fetches it as a blob)."""
    await _get_owned_post(post_id, current_user, db)
    media = await _get_media(post_id, media_id, db)
    try:
        path = resolve_media_path(settings.media_storage_path, media.file_path)
    except ValueError:
        logger.error(f"Media {media.id} has an invalid path")
        raise HTTPException(status_code=404, detail="File not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type=media.mime_type or "application/octet-stream")


@router.delete("/{post_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    post_id: int,
    media_id: int,
    current_user: User = Depends(get_current_user_webapp_or_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Remove an image from a post."""
    post = await _get_owned_post(post_id, current_user, db)
    if post.status == "published":
        raise HTTPException(status_code=409, detail="Cannot change media of a published post")
    media = await _get_media(post_id, media_id, db)

    relpath = media.file_path
    await db.delete(media)
    await db.commit()

    try:
        path = resolve_media_path(settings.media_storage_path, relpath)
        await run_in_threadpool(lambda: path.unlink(missing_ok=True))
    except (ValueError, OSError) as e:
        logger.warning(f"Could not remove media file {relpath}: {e}")
    return None
