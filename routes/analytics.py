from datetime import date, datetime, time, UTC
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.cache import analytics_cache
from helpers.db import get_session
from helpers.dependencies import get_current_user, get_current_business
from models.business import Business
from models.business_user import BusinessUser
from models.feedback_request import FeedbackRequest

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def build_datetime_range(
    from_date: Optional[date],
    to_date: Optional[date],
) -> tuple[Optional[datetime], Optional[datetime]]:
    from_dt = None
    to_dt = None

    if from_date is not None:
        from_dt = datetime.combine(from_date, time.min).replace(tzinfo=UTC)

    if to_date is not None:
        to_dt = datetime.combine(to_date, time.max).replace(tzinfo=UTC)

    return from_dt, to_dt


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    kpi_from: Optional[date] = None,
    kpi_to: Optional[date] = None,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
    session: AsyncSession = Depends(get_session),
):
    kpi_from_str = kpi_from.isoformat() if kpi_from else "all"
    kpi_to_str = kpi_to.isoformat() if kpi_to else "all"
    analytics_cache_key = f"analytics:{current_business.id}:{kpi_from_str}:{kpi_to_str}"

    cached_summary = analytics_cache.get(analytics_cache_key)

    if cached_summary is None:
        from_dt, to_dt = build_datetime_range(kpi_from, kpi_to)

        base_conditions = [FeedbackRequest.business_id == current_business.id]

        if from_dt is not None:
            base_conditions.append(FeedbackRequest.sent_at >= from_dt)

        if to_dt is not None:
            base_conditions.append(FeedbackRequest.sent_at <= to_dt)

        total_requests_stmt = select(func.count()).where(*base_conditions)
        total_requests = (await session.exec(total_requests_stmt)).one()

        total_responses_stmt = select(func.count()).where(
            *base_conditions,
            FeedbackRequest.responded_at.is_not(None),
        )
        total_responses = (await session.exec(total_responses_stmt)).one()

        avg_score_stmt = select(func.avg(FeedbackRequest.rating)).where(
            *base_conditions,
            FeedbackRequest.rating.is_not(None),
        )
        avg_score = (await session.exec(avg_score_stmt)).one()

        comment_count_stmt = select(func.count()).where(
            *base_conditions,
            FeedbackRequest.comment.is_not(None),
            FeedbackRequest.comment != "",
        )
        comment_count = (await session.exec(comment_count_stmt)).one()

        distribution_stmt = (
            select(FeedbackRequest.rating, func.count())
            .where(
                *base_conditions,
                FeedbackRequest.rating.is_not(None),
            )
            .group_by(FeedbackRequest.rating)
        )
        distribution_rows = (await session.exec(distribution_stmt)).all()

        score_distribution = {score: 0 for score in range(1, 11)}
        for rating, count in distribution_rows:
            if rating in score_distribution:
                score_distribution[rating] = count

        response_rate = None
        if total_requests > 0:
            response_rate = round((total_responses / total_requests) * 100, 2)

        comment_rate = None
        if total_responses > 0:
            comment_rate = round((comment_count / total_responses) * 100, 2)

        summary = {
            "avg_score": round(float(avg_score), 2) if avg_score is not None else None,
            "response_rate": response_rate,
            "total_requests": total_requests,
            "total_responses": total_responses,
            "comment_rate": comment_rate,
            "score_distribution": score_distribution,
        }

        analytics_cache.set(analytics_cache_key, summary, ttl_seconds=60)
    else:
        summary = cached_summary

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