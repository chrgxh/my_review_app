import hashlib
import secrets
from datetime import datetime, timedelta, UTC


RESET_TOKEN_TTL_HOURS = 1


def generate_raw_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_reset_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=RESET_TOKEN_TTL_HOURS)