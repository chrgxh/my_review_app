from datetime import datetime, timedelta, UTC
from typing import Any

from loguru import logger


class TTLCache:
    def __init__(self, name: str = "cache") -> None:
        self._store: dict[str, tuple[Any, datetime]] = {}
        self.name = name

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)

        if item is None:
            logger.debug(f"[{self.name}] MISS key={key}")
            return None

        value, expires_at = item

        if datetime.now(UTC) >= expires_at:
            logger.debug(f"[{self.name}] EXPIRED key={key}")
            self._store.pop(key, None)
            return None

        logger.debug(f"[{self.name}] HIT key={key}")
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._store[key] = (value, expires_at)

        logger.debug(
            f"[{self.name}] SET key={key} ttl={ttl_seconds}s"
        )

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        logger.debug(f"[{self.name}] DELETE key={key}")

    def clear(self) -> None:
        self._store.clear()
        logger.debug(f"[{self.name}] CLEAR all")


business_cache = TTLCache("business_cache")
analytics_cache = TTLCache("analytics_cache")