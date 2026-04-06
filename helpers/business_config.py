from datetime import datetime, UTC
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones
import re

from fastapi import UploadFile


MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
LOGO_UPLOAD_DIR = Path("static/logos")


def format_utc_offset(tz_name: str) -> str:
    now_utc = datetime.now(UTC)
    tz = ZoneInfo(tz_name)
    offset = now_utc.astimezone(tz).utcoffset()

    if offset is None:
        return "UTC+00:00"

    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60

    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def build_timezone_options() -> list[dict[str, str]]:
    return [
        {
            "value": tz,
            "label": f"{tz} ({format_utc_offset(tz)})",
        }
        for tz in sorted(available_timezones())
    ]


def is_valid_timezone(timezone: str) -> bool:
    return timezone in available_timezones()


def normalize_slug(slug: str) -> str:
    normalized = slug.strip().lower()

    if not re.fullmatch(r"[a-z0-9-]+", normalized):
        raise ValueError(
            "Email name may only contain lowercase letters, numbers, and hyphens."
        )

    return normalized


def build_from_email_from_slug(
    slug: str,
    configured_from_email: str,
) -> str:
    configured_from_email = configured_from_email.strip()

    if "@" not in configured_from_email:
        raise ValueError("Configured from_email is invalid.")

    domain = configured_from_email.split("@", 1)[1]
    return f"{slug}@{domain}"


def is_local_managed_logo_url(
    logo_url: str | None,
    base_url: str,
) -> bool:
    if not logo_url:
        return False

    expected_prefix = f"{base_url}/static/logos/"
    return logo_url.startswith(expected_prefix)


def local_logo_path_for_slug(slug: str) -> Path:
    return LOGO_UPLOAD_DIR / f"{slug}.png"


def public_logo_url_for_slug(
    base_url: str,
    slug: str,
) -> str:
    return f"{base_url}/static/logos/{slug}.png"


async def update_logo_asset(
    *,
    logo: UploadFile | None,
    old_slug: str,
    new_slug: str,
    old_logo_url: str | None,
    base_url: str,
) -> str | None:
    LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    old_logo_path = local_logo_path_for_slug(old_slug)
    new_logo_path = local_logo_path_for_slug(new_slug)

    updated_logo_url = old_logo_url

    # Rename managed local logo when slug changes and no new upload yet
    if (
        old_slug != new_slug
        and is_local_managed_logo_url(old_logo_url, base_url)
        and old_logo_path.exists()
    ):
        if new_logo_path.exists():
            new_logo_path.unlink()

        old_logo_path.rename(new_logo_path)
        updated_logo_url = public_logo_url_for_slug(base_url, new_slug)

    # Save new upload if provided
    if logo and logo.filename:
        content_type = (logo.content_type or "").lower()
        filename_lower = logo.filename.lower()

        if content_type != "image/png" and not filename_lower.endswith(".png"):
            raise ValueError("Logo must be a PNG file.")

        content = await logo.read()

        if len(content) > MAX_LOGO_SIZE_BYTES:
            raise ValueError("Logo is too large. Maximum size is 2 MB.")

        with open(new_logo_path, "wb") as f:
            f.write(content)

        updated_logo_url = public_logo_url_for_slug(base_url, new_slug)

        if (
            old_slug != new_slug
            and is_local_managed_logo_url(old_logo_url, base_url)
            and old_logo_path.exists()
            and old_logo_path != new_logo_path
        ):
            old_logo_path.unlink(missing_ok=True)

    return updated_logo_url