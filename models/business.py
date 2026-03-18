from datetime import datetime, UTC
from typing import Optional

from sqlmodel import SQLModel, Field

class Business(SQLModel, table=True):
    __tablename__ = "businesses"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    from_email: str
    reply_to_email: Optional[str] = None
    logo_url: Optional[str] = None
    default_email_text: Optional[str] = None
    review_redirect_url: Optional[str] = None
    timezone: str = "UTC"
    # IANA timezone format (e.g. "Europe/Athens") is required.
    # This ensures correct handling of daylight saving time and compatibility with Python's zoneinfo.
    subscription_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))