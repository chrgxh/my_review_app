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


async def get_business_by_slug(
    session: AsyncSession,
    slug: str,
) -> Optional[Business]:
    result = await session.exec(
        select(Business).where(Business.slug == slug)
    )
    return result.first()


async def is_business_slug_unique(
    session: AsyncSession,
    slug: str,
    exclude_business_id: Optional[int] = None,
) -> bool:
    statement = select(Business).where(Business.slug == slug)

    if exclude_business_id is not None:
        statement = statement.where(Business.id != exclude_business_id)

    result = await session.exec(statement)
    existing = result.first()
    return existing is None


async def save_business(
    session: AsyncSession,
    business: Business,
) -> Business:
    session.add(business)
    await session.commit()
    await session.refresh(business)
    return business