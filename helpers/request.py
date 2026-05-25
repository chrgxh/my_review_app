"""Request-derived helpers shared across routes and middleware.

Kept dependency-free (only Starlette/FastAPI's ``Request``) so it can be
imported from anywhere — including ``helpers.rate_limit`` — without risking
circular imports.
"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP for a request behind Nginx.

    Resolution order (most → least trustworthy for a single trusted proxy):
      1. ``X-Real-IP`` — set by our Nginx to the actual socket peer; the
         client cannot forge it.
      2. The *last* entry in ``X-Forwarded-For`` — the hop Nginx appended via
         ``$proxy_add_x_forwarded_for``. We deliberately do NOT use the first
         entry: Nginx appends rather than strips, so the first entry is
         attacker-supplied and would let a client bypass per-IP rate limits.
      3. ``request.client.host`` (direct connection / no proxy).
      4. The literal string ``"unknown"`` when no client is available.
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        last_ip = forwarded_for.split(",")[-1].strip()
        if last_ip:
            return last_ip

    if request.client is not None and request.client.host:
        return request.client.host

    return "unknown"


def mask_token(token: str | None) -> str:
    """Return a log-safe representation of a secret token.

    Never log feedback/reset tokens in full. We keep only the first 6
    characters (enough to correlate logs) followed by an ellipsis.
    """
    if not token:
        return "none"
    return f"{token[:6]}..."
