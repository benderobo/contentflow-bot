"""Telegram WebApp authentication utilities."""
import hmac
import hashlib
from typing import Optional, Dict, Any
from urllib.parse import unquote, parse_qsl


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
        # Parse init_data query string
        params = dict(parse_qsl(unquote(init_data)))

        if "hash" not in params:
            return None

        received_hash = params.pop("hash")

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

        # Compare hashes
        if calculated_hash != received_hash:
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
