import httpx
import os
from typing import Optional

API_URL = os.getenv("API_URL", "http://api:8000")
API_KEY = os.environ["API_KEY"]


async def make_authenticated_request(
    method: str,
    endpoint: str,
    **kwargs
) -> Optional[httpx.Response]:
    """Make authenticated request to API with service credentials."""
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_KEY}"
    headers["X-Service-Account"] = "bot"

    try:
        async with httpx.AsyncClient() as client:
            url = f"{API_URL}{endpoint}"
            response = await client.request(method, url, headers=headers, **kwargs)
            return response
    except Exception as e:
        print(f"API request error: {e}")
        return None
