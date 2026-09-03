"""Telegram WebApp authentication utilities."""
import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from urllib.parse import parse_qsl


def verify_webapp_init_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Telegram WebApp initData signature.

    Args:
        init_data: Raw initData string from Telegram.WebApp.initData
        bot_token: Bot token from settings

    Returns:
        Parsed user/app data if signature is valid, None otherwise
    """
    if not init_data or not bot_token:
        return None

    try:
        # Parse init_data query string (parse_qsl already URL-decodes each value)
        params = dict(parse_qsl(init_data))

        if "hash" not in params:
            return None

        received_hash = params.pop("hash")

        # Check auth_date freshness (prevent replay attacks)
        auth_date = params.get("auth_date", "0")
        try:
            if time.time() - int(auth_date) > 86400:  # 24 hours
                return None
        except (ValueError, TypeError):
            return None

        # Create data check string (sorted by keys, newline separated)
        data_check_arr = [f"{k}={v}" for k, v in sorted(params.items())]
        data_check_string = "\n".join(data_check_arr)

        # Calculate secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        # Parse user data if present
        if "user" in params:
            import json
            try:
                user_data = json.loads(params["user"])
                return {"user": user_data, **{k: v for k, v in params.items() if k != "user"}}
            except (json.JSONDecodeError, TypeError):
                pass

        return params

    except Exception:
        return None
