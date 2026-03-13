from typing import Optional

from sqlmodel import Session
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