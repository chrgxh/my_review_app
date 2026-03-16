from typing import Optional

from sqlmodel import Session, select

from models.business import Business


def get_business_by_id(session: Session, business_id: int) -> Optional[Business]:
    return session.exec(
        select(Business).where(Business.id == business_id)
    ).first()