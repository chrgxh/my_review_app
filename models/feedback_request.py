from datetime import datetime,UTC
from typing import Optional

from sqlmodel import SQLModel, Field

class FeedbackRequest(SQLModel, table=True):
    __tablename__ = "feedback_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="businesses.id", index=True)
    sent_by_user_id: int = Field(foreign_key="business_users.id", index=True)
    recipient_email: str = Field(index=True)
    identifier: str
    message: Optional[str] = None
    token: str = Field(index=True, unique=True)
    email_provider_id: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="sent", index=True)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    opened_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    rating: Optional[int] = None
    comment: Optional[str] = None