"""Helpers for validating and storing post images."""
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Tuple

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # Telegram photo limit (10 MB)
MAX_IMAGES_PER_POST = 10  # Telegram media group limit


def detect_image_type(data: bytes) -> Optional[Tuple[str, str]]:
    """Detect image type from magic bytes. Returns (extension, mime) or None.

    The client-supplied Content-Type and filename are never trusted.
    Only formats Telegram accepts for sendPhoto are allowed.
    """
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_media_relpath(post_id: int, ext: str) -> str:
    """Server-generated relative path; the original filename is discarded."""
    return f"{post_id}/{uuid.uuid4().hex}.{ext}"


def resolve_media_path(root: str, relpath: str) -> Path:
    """Resolve a stored relative path inside the media root.

    Raises ValueError if the result would escape the root (path traversal).
    """
    root_path = Path(root).resolve()
    full = (root_path / relpath).resolve()
    if root_path != full and root_path not in full.parents:
        raise ValueError("media path escapes storage root")
    return full
