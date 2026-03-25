from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import settings


COOKIE_NAME = "auth_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def get_auth_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="auth-cookie")


def create_session_token(user_id: int) -> str:
    serializer = get_auth_serializer()
    return serializer.dumps({"user_id": user_id})


def verify_session_token(
    token: str,
    max_age_seconds: int = COOKIE_MAX_AGE,
) -> int | None:
    serializer = get_auth_serializer()

    try:
        data = serializer.loads(token, max_age=max_age_seconds)
        return int(data["user_id"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError):
        return None