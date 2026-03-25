import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from pwdlib import PasswordHash
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.db import engine, create_db_and_tables
from models.business import Business
from models.business_user import BusinessUser

password_hasher = PasswordHash.recommended()


def load_config():
    config_path = Path("scripts/seed_config.yaml")

    if not config_path.exists():
        raise RuntimeError("seed_config.yaml not found")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def main():
    await create_db_and_tables()

    config = load_config()

    business_cfg = config["business"]
    user_cfg = config["user"]

    async with AsyncSession(engine) as session:
        existing_business_result = await session.exec(
            select(Business).where(Business.slug == business_cfg["slug"])
        )
        existing_business = existing_business_result.first()

        if existing_business is None:
            business = Business(
                name=business_cfg["name"],
                slug=business_cfg["slug"],
                from_email=business_cfg["from_email"],
                reply_to_email=business_cfg.get("reply_to_email"),
                logo_url=business_cfg.get("logo_url"),
                default_email_text=business_cfg.get("default_email_text"),
                review_redirect_url=business_cfg.get("review_redirect_url"),
                subscription_end=datetime.now(timezone.utc)
                + timedelta(days=business_cfg.get("subscription_days", 365)),
            )

            session.add(business)
            await session.commit()
            await session.refresh(business)

            print(f"Created business: {business.name}")
        else:
            business = existing_business
            print(f"Business already exists: {business.name}")

        existing_user_result = await session.exec(
            select(BusinessUser).where(BusinessUser.email == user_cfg["email"])
        )
        existing_user = existing_user_result.first()

        if existing_user is None:
            user = BusinessUser(
                business_id=business.id,
                email=user_cfg["email"],
                password_hash=password_hasher.hash(user_cfg["password"]),
                full_name=user_cfg.get("full_name"),
                is_active=True,
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)

            print(f"Created business user: {user.email}")
        else:
            print(f"User already exists: {existing_user.email}")


if __name__ == "__main__":
    asyncio.run(main())