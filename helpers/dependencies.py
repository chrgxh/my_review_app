from fastapi import Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.db import get_session
from helpers.auth import COOKIE_NAME, verify_session_token
from models.business import Business
from models.business_user import BusinessUser
from repositories.business_user_repository import get_business_user_by_id


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> BusinessUser:
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = verify_session_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = await get_business_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> BusinessUser:
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = verify_session_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = await get_business_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_business(
    current_user: BusinessUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Business:
    statement = select(Business).where(Business.id == current_user.business_id)
    result = await session.exec(statement)
    business = result.first()

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Business not found",
        )

    return business