from datetime import datetime, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def format_datetime_for_business(dt: datetime, timezone_name: str | None) -> str:
    try:
        tz = ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    # SQLite may return naive datetimes after reading from DB.
    # In this app, naive timestamps should be interpreted as UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    local_dt = dt.astimezone(tz)

    offset_hours = int(local_dt.utcoffset().total_seconds() / 3600)
    offset_str = f"UTC{offset_hours:+d}"

    return local_dt.strftime(f"%d %b %Y, %H:%M (%Z, {offset_str})")