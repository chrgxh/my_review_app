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

    offset = local_dt.utcoffset()
    if offset is None:
        offset_str = "UTC+0"
    else:
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if minutes == 0:
            offset_str = f"UTC{sign}{hours}"
        else:
            offset_str = f"UTC{sign}{hours}:{minutes:02d}"

    return local_dt.strftime(f"%d %b %Y, %H:%M (%Z, {offset_str})")