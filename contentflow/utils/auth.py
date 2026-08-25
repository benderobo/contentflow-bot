import hmac
import hashlib
import os
from typing import Optional

# Shared secret for HMAC-based user ID verification
SHARED_SECRET = os.environ.get("AUTH_SHARED_SECRET", os.environ.get("SECRET_KEY", ""))


def sign_user_id(user_id: int) -> str:
    """Generate HMAC signature for user_id to prevent spoofing."""
    if not SHARED_SECRET:
        raise ValueError("AUTH_SHARED_SECRET or SECRET_KEY must be set")

    message = str(user_id).encode()
    signature = hmac.new(
        SHARED_SECRET.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_user_id(user_id: int, signature: str) -> bool:
    """Verify HMAC signature for user_id."""
    if not SHARED_SECRET:
        return False

    try:
        expected_signature = sign_user_id(user_id)
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False
