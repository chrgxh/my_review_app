from datetime import datetime, UTC
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.feedback_request import FeedbackRequest


async def create_feedback_request(
    session: AsyncSession,
    *,
    business_id: int,
    sent_by_user_id: int,
    recipient_email: str,
    identifier: str,
    message: Optional[str],
    token: str,
    email_provider_id: Optional[str],
) -> FeedbackRequest:
    feedback_request = FeedbackRequest(
        business_id=business_id,
        sent_by_user_id=sent_by_user_id,
        recipient_email=recipient_email,
        identifier=identifier,
        message=message,
        token=token,
        email_provider_id=email_provider_id,
        status="sent",
    )

    session.add(feedback_request)
    await session.commit()
    await session.refresh(feedback_request)

    return feedback_request


async def get_feedback_request_by_token(
    session: AsyncSession,
    token: str,
) -> Optional[FeedbackRequest]:
    result = await session.exec(
        select(FeedbackRequest).where(FeedbackRequest.token == token)
    )
    return result.first()


async def respond_to_feedback_request(
    session: AsyncSession,
    feedback_request: FeedbackRequest,
    score: int,
    comment: str | None,
) -> FeedbackRequest:
    feedback_request.rating = score
    feedback_request.comment = comment.strip() if comment and comment.strip() else None
    feedback_request.responded_at = datetime.now(UTC)
    feedback_request.status = "responded"

    session.add(feedback_request)
    await session.commit()
    await session.refresh(feedback_request)

    return feedback_request