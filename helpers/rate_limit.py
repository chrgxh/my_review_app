"""Central slowapi configuration.

The ``limiter`` is created here (not in ``main.py``) so route modules can
import it for ``@limiter.limit(...)`` decorators without importing the app,
which would create a circular import.

In-memory storage is used by default, which is fine for a single-process
deployment on a small VPS. To move to Redis later, pass
``storage_uri="redis://..."`` to ``Limiter`` — no other changes needed.
"""

from loguru import logger

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from helpers.request import get_client_ip

# Per-IP limiter. The key function is what decides "who" is being limited.
limiter = Limiter(key_func=get_client_ip)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Log the blocked attempt and return a standard 429 response."""
    client_ip = get_client_ip(request)
    # ``exc.detail`` holds the limit that was exceeded, e.g. "5 per 1 minute".
    limit = getattr(exc, "detail", None)

    logger.warning(
        f"Rate limit exceeded | client_ip={client_ip} "
        f"| path={request.url.path} | method={request.method} | limit={limit}"
    )

    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down and try again later."},
    )

    # Mirror slowapi's default handler so the standard rate-limit headers
    # (Retry-After, X-RateLimit-*) are still emitted.
    try:
        response = request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )
    except Exception:  # pragma: no cover - headers are best-effort
        pass

    return response
