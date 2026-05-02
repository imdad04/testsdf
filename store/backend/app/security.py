"""Telegram WebApp initData verification.

Implements the HMAC-SHA256 scheme described at
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Without this, any client could spoof someone else's Telegram user id.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import get_settings


class AuthError(Exception):
    pass


def parse_init_data(init_data: str, max_age_sec: int = 86400) -> dict:
    """Verify the signature of Telegram's WebApp initData and return parsed dict.

    Raises AuthError on tampering or expiry.
    """
    if not init_data:
        raise AuthError("empty initData")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise AuthError("no hash in initData")

    auth_date = int(parsed.get("auth_date", "0"))
    if auth_date and time.time() - auth_date > max_age_sec:
        raise AuthError("initData expired")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    secret_key = hmac.new(
        b"WebAppData", get_settings().bot_token.encode(), hashlib.sha256
    ).digest()
    calc_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise AuthError("bad signature")

    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except json.JSONDecodeError:
            raise AuthError("bad user payload")

    return parsed


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set
