from datetime import date, datetime, time, UTC
from typing import Optional

from sqlmodel import func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.cache import analytics_cache
from models.feedback_request import FeedbackRequest

PAGE_SIZE = 25


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


def parse_optional_date(value: Optional[str]) -> Optional[date]:
    if value is None or value.strip() == "":
        return None
    return date.fromisoformat(value)


def parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value.strip() == "":
        return None
    return int(value)


async def get_analytics_summary(
    session: AsyncSession,
    business_id: int,
    kpi_from: Optional[date],
    kpi_to: Optional[date],
) -> dict:
    kpi_from_str = kpi_from.isoformat() if kpi_from else "all"
    kpi_to_str = kpi_to.isoformat() if kpi_to else "all"
    analytics_cache_key = f"analytics:{business_id}:{kpi_from_str}:{kpi_to_str}"

    cached_summary = analytics_cache.get(analytics_cache_key)
    if cached_summary is not None:
        return cached_summary

    from_dt, to_dt = build_datetime_range(kpi_from, kpi_to)

    base_conditions = [FeedbackRequest.business_id == business_id]

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

    analytics_cache.set(analytics_cache_key, summary, ttl_seconds=60 * 10)
    return summary


def build_records_conditions(
    business_id: int,
    recipient_email: str = "",
    identifier: str = "",
    responded_state: str = "",
    rating: Optional[int] = None,
    has_comment: str = "",
    sent_from: Optional[date] = None,
    sent_to: Optional[date] = None,
) -> list:
    conditions = [FeedbackRequest.business_id == business_id]

    if recipient_email.strip():
        conditions.append(
            FeedbackRequest.recipient_email.ilike(f"%{recipient_email.strip()}%")
        )

    if identifier.strip():
        conditions.append(
            FeedbackRequest.identifier.ilike(f"%{identifier.strip()}%")
        )

    if responded_state == "responded":
        conditions.append(FeedbackRequest.responded_at.is_not(None))
    elif responded_state == "not_responded":
        conditions.append(FeedbackRequest.responded_at.is_(None))

    if rating is not None:
        conditions.append(FeedbackRequest.rating == rating)

    if has_comment == "yes":
        conditions.append(FeedbackRequest.comment.is_not(None))
        conditions.append(FeedbackRequest.comment != "")
    elif has_comment == "no":
        conditions.append(
            or_(
                FeedbackRequest.comment.is_(None),
                FeedbackRequest.comment == "",
            )
        )

    sent_from_dt, sent_to_dt = build_datetime_range(sent_from, sent_to)

    if sent_from_dt is not None:
        conditions.append(FeedbackRequest.sent_at >= sent_from_dt)

    if sent_to_dt is not None:
        conditions.append(FeedbackRequest.sent_at <= sent_to_dt)

    return conditions


async def search_feedback_records(
    session: AsyncSession,
    business_id: int,
    recipient_email: str = "",
    identifier: str = "",
    responded_state: str = "",
    rating: Optional[int] = None,
    has_comment: str = "",
    sent_from: Optional[date] = None,
    sent_to: Optional[date] = None,
    page: int = 1,
) -> dict:
    if page < 1:
        page = 1

    conditions = build_records_conditions(
        business_id=business_id,
        recipient_email=recipient_email,
        identifier=identifier,
        responded_state=responded_state,
        rating=rating,
        has_comment=has_comment,
        sent_from=sent_from,
        sent_to=sent_to,
    )

    total_stmt = select(func.count()).where(*conditions)
    records_total = (await session.exec(total_stmt)).one()

    total_pages = (records_total + PAGE_SIZE - 1) // PAGE_SIZE if records_total > 0 else 0

    if total_pages > 0 and page > total_pages:
        page = total_pages

    offset = (page - 1) * PAGE_SIZE

    records_stmt = (
        select(FeedbackRequest)
        .where(*conditions)
        .order_by(FeedbackRequest.sent_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    records = (await session.exec(records_stmt)).all()

    return {
        "records": records,
        "records_total": records_total,
        "page": page,
        "total_pages": total_pages,
        "page_size": PAGE_SIZE,
    }