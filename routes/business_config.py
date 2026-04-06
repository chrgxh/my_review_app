from datetime import datetime, UTC
from zoneinfo import available_timezones, ZoneInfo

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from models.business import Business
from models.business_user import BusinessUser
from helpers.dependencies import get_current_user, get_current_business


router = APIRouter()
templates = Jinja2Templates(directory="templates")


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


@router.get("/business-config", response_class=HTMLResponse)
async def business_config_page(
    request: Request,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    timezone_options = [
        {
            "value": tz,
            "label": f"{tz} ({format_utc_offset(tz)})",
        }
        for tz in sorted(available_timezones())
    ]

    return templates.TemplateResponse(
        "business_config.html",
        {
            "request": request,
            "current_user": current_user,
            "current_business": current_business,
            "timezone_options": timezone_options,
        },
    )