from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.business import Business


async def get_business_by_id(
    session: AsyncSession,
    business_id: int,
) -> Optional[Business]:
    result = await session.exec(
        select(Business).where(Business.id == business_id)
    )
    return result.first()