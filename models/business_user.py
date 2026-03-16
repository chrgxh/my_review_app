from datetime import datetime, UTC
from typing import Optional

from sqlmodel import SQLModel, Field

class BusinessUser(SQLModel, table=True):
    __tablename__ = "business_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="businesses.id", index=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))