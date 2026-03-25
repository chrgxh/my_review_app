from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.business_user import BusinessUser


async def get_business_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> BusinessUser | None:
    statement = select(BusinessUser).where(BusinessUser.id == user_id)
    result = await session.exec(statement)
    return result.first()


async def get_business_user_by_email(
    session: AsyncSession,
    email: str,
) -> BusinessUser | None:
    statement = select(BusinessUser).where(BusinessUser.email == email)
    result = await session.exec(statement)
    return result.first()