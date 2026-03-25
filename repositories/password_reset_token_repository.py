from datetime import datetime, UTC

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.password_reset_token import PasswordResetToken


async def create_password_reset_token(
    session: AsyncSession,
    user_id: int,
    token_hash: str,
    expires_at,
) -> PasswordResetToken:
    reset_token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(reset_token)
    await session.commit()
    await session.refresh(reset_token)
    return reset_token


async def get_valid_password_reset_token(
    session: AsyncSession,
    token_hash: str,
) -> PasswordResetToken | None:
    statement = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.now(UTC),
    )
    result = await session.exec(statement)
    return result.first()


async def mark_password_reset_token_used(
    session: AsyncSession,
    reset_token: PasswordResetToken,
) -> None:
    reset_token.used_at = datetime.now(UTC)
    session.add(reset_token)
    await session.commit()

async def invalidate_user_password_reset_tokens(
    session: AsyncSession,
    user_id: int,
) -> None:
    statement = select(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
    )
    result = await session.exec(statement)
    tokens = result.all()

    now = datetime.now(UTC)
    for token in tokens:
        token.used_at = now
        session.add(token)

    await session.commit()