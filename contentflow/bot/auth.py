import httpx
import os
import logging
from typing import Optional
from utils.auth import sign_user_id

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://api:8000")
API_KEY = os.environ["API_KEY"]


async def make_authenticated_request(
    method: str,
    endpoint: str,
    user_id: Optional[int] = None,
    **kwargs
) -> Optional[httpx.Response]:
    """Make authenticated request to API with service credentials."""
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_KEY}"
    headers["X-Service-Account"] = "bot"

    # If user_id is provided, add HMAC signature (in json body or query params)
    if user_id:
        signature = sign_user_id(user_id)
        if "json" in kwargs:
            kwargs["json"]["user_signature"] = signature
        elif "params" in kwargs:
            kwargs["params"]["user_signature"] = signature
        else:
            # If no params dict yet, add user_id to endpoint URL
            separator = "&" if "?" in endpoint else "?"
            endpoint = f"{endpoint}{separator}user_id={user_id}&user_signature={signature}"

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            url = f"{API_URL}{endpoint}"
            logger.debug(f"API request: {method} {url}")
            response = await client.request(method, url, headers=headers, **kwargs)
            return response
    except Exception as e:
        logger.error(f"API request error: {method} {endpoint} - {type(e).__name__}: {e}")
        return None
