from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.analytics import (
    get_analytics_summary,
    parse_optional_date,
    parse_optional_int,
    search_feedback_records,
)
from helpers.datetime_formatter import format_datetime_for_business
from helpers.db import get_session
from helpers.dependencies import get_current_user, get_current_business
from helpers.rate_limit import limiter
from models.business import Business
from models.business_user import BusinessUser

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/analytics/records", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def analytics_records(
    request: Request,
    recipient_email: str = "",
    identifier: str = "",
    responded_state: str = "",
    rating: Optional[str] = None,
    has_comment: str = "",
    sent_from: Optional[str] = None,
    sent_to: Optional[str] = None,
    page: int = 1,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
    session: AsyncSession = Depends(get_session),
):
    parsed_rating = parse_optional_int(rating)
    parsed_sent_from = parse_optional_date(sent_from)
    parsed_sent_to = parse_optional_date(sent_to)

    records_result = await search_feedback_records(
        session=session,
        business_id=current_business.id,
        recipient_email=recipient_email,
        identifier=identifier,
        responded_state=responded_state,
        rating=parsed_rating,
        has_comment=has_comment,
        sent_from=parsed_sent_from,
        sent_to=parsed_sent_to,
        page=page,
    )

    return templates.TemplateResponse(
        "analytics_records.html",
        {
            "request": request,
            "current_user": current_user,
            "current_business": current_business,
            "records": records_result["records"],
            "records_total": records_result["records_total"],
            "page": records_result["page"],
            "total_pages": records_result["total_pages"],
            "recipient_email": recipient_email,
            "identifier": identifier,
            "responded_state": responded_state,
            "rating": parsed_rating,
            "has_comment": has_comment,
            "sent_from": parsed_sent_from,
            "sent_to": parsed_sent_to,
            "format_datetime": format_datetime_for_business,
        },
    )


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    kpi_from: Optional[date] = None,
    kpi_to: Optional[date] = None,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
    session: AsyncSession = Depends(get_session),
):
    summary = await get_analytics_summary(
        session=session,
        business_id=current_business.id,
        kpi_from=kpi_from,
        kpi_to=kpi_to,
    )

    return templates.TemplateResponse(
        "analytics_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "current_business": current_business,
            "kpi_from": kpi_from,
            "kpi_to": kpi_to,
            "avg_score": summary["avg_score"],
            "response_rate": summary["response_rate"],
            "total_requests": summary["total_requests"],
            "total_responses": summary["total_responses"],
            "comment_rate": summary["comment_rate"],
            "score_distribution": summary["score_distribution"],
        },
    )