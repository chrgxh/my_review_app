from fastapi import Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.cache import business_cache
from helpers.db import get_session
from helpers.auth import COOKIE_NAME, verify_session_token
from models.business import Business
from models.business_user import BusinessUser
from repositories.business_user_repository import get_business_user_by_id


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> BusinessUser | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    user_id = verify_session_token(token)
    if user_id is None:
        return None

    user = await get_business_user_by_id(session, user_id)
    if user is None or not user.is_active:
        return None

    return user


async def get_current_user(
    current_user: BusinessUser | None = Depends(get_current_user_optional),
) -> BusinessUser:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return current_user


async def get_current_business(
    current_user: BusinessUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Business:
    business_cache_key = f"business:{current_user.business_id}"
    cached_business = business_cache.get(business_cache_key)

    if cached_business is not None:
        return cached_business

    statement = select(Business).where(Business.id == current_user.business_id)
    result = await session.exec(statement)
    business = result.first()

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Business not found",
        )

    business_cache.set(business_cache_key, business, ttl_seconds=300)
    return business