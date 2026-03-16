from datetime import datetime, UTC
from typing import Optional

from sqlmodel import Session, select
from models.feedback_request import FeedbackRequest


def create_feedback_request(
    session: Session,
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
    session.commit()
    session.refresh(feedback_request)

    return feedback_request

def get_feedback_request_by_token(
    session: Session,
    token: str,
) -> Optional[FeedbackRequest]:
    return session.exec(
        select(FeedbackRequest).where(FeedbackRequest.token == token)
    ).first()


def respond_to_feedback_request(
    session: Session,
    feedback_request: FeedbackRequest,
    score: int,
    comment: str | None,
) -> FeedbackRequest:
    feedback_request.rating = score
    feedback_request.comment = comment.strip() if comment and comment.strip() else None
    feedback_request.responded_at = datetime.now(UTC)
    feedback_request.status = "responded"

    session.add(feedback_request)
    session.commit()
    session.refresh(feedback_request)

    return feedback_request