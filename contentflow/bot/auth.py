import httpx
import os
from typing import Optional

API_URL = os.getenv("API_URL", "http://api:8000")

# Global token storage (in production use Redis)
_bot_token: Optional[str] = None


async def get_bot_token() -> str:
    """Get or refresh bot API token."""
    global _bot_token

    if _bot_token:
        return _bot_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/auth/bot-token",
                json={
                    "bot_id": os.getenv("BOT_TOKEN", "")[:30]  # Use first 30 chars of token as ID
                }
            )
            if response.status_code == 200:
                data = response.json()
                _bot_token = data["access_token"]
                return _bot_token
    except Exception as e:
        print(f"Error getting bot token: {e}")

    return None


async def make_authenticated_request(
    method: str,
    endpoint: str,
    **kwargs
) -> Optional[httpx.Response]:
    """Make authenticated request to API."""
    token = await get_bot_token()
    if not token:
        return None

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient() as client:
            url = f"{API_URL}{endpoint}"
            response = await client.request(method, url, headers=headers, **kwargs)
            return response
    except Exception as e:
        print(f"API request error: {e}")
        return None
