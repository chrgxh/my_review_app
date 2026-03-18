"""
Example run as module:

python -m scripts.update_business_by_id --id 1 --review-redirect-url https://google.com
python -m scripts.update_business_by_id --id 1 --from-email onboarding@resend.dev --reply-to-email example@examplemail.com
python -m scripts.update_business_by_id --id 2 --name "My Hotel" --slug my-hotel --logo-url https://example.com/logo.png
python -m scripts.update_business_by_id --id 1 --timezone Europe/Athens
"""

import argparse
import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.db import engine
from models.business import Business


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update a business by id.")

    parser.add_argument("--id", type=int, required=True, help="Business id to update")
    parser.add_argument("--name", type=str, help="Business name")
    parser.add_argument("--slug", type=str, help="Business slug")
    parser.add_argument("--from-email", dest="from_email", type=str, help="From email")
    parser.add_argument("--reply-to-email", dest="reply_to_email", type=str, help="Reply-to email")
    parser.add_argument("--logo-url", dest="logo_url", type=str, help="Logo URL")
    parser.add_argument(
        "--default-email-text",
        dest="default_email_text",
        type=str,
        help="Default email text",
    )
    parser.add_argument(
        "--review-redirect-url",
        dest="review_redirect_url",
        type=str,
        help="Public review redirect URL",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        help='Business timezone in IANA format, e.g. "Europe/Athens"',
    )

    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    async with AsyncSession(engine) as session:
        business = await session.get(Business, args.id)

        if business is None:
            print(f"Business with id={args.id} not found")
            return

        updated_fields: list[str] = []

        if args.name is not None:
            business.name = args.name
            updated_fields.append("name")

        if args.slug is not None:
            business.slug = args.slug
            updated_fields.append("slug")

        if args.from_email is not None:
            business.from_email = args.from_email
            updated_fields.append("from_email")

        if args.reply_to_email is not None:
            business.reply_to_email = args.reply_to_email
            updated_fields.append("reply_to_email")

        if args.logo_url is not None:
            business.logo_url = args.logo_url
            updated_fields.append("logo_url")

        if args.default_email_text is not None:
            business.default_email_text = args.default_email_text
            updated_fields.append("default_email_text")

        if args.review_redirect_url is not None:
            business.review_redirect_url = args.review_redirect_url
            updated_fields.append("review_redirect_url")

        if args.timezone is not None:
            business.timezone = args.timezone
            updated_fields.append("timezone")

        if not updated_fields:
            print("No update fields were provided")
            return

        session.add(business)
        await session.commit()
        await session.refresh(business)

        print("Updated business:")
        print(f"id={business.id}")
        print(f"name={business.name}")
        print(f"slug={business.slug}")
        print(f"from_email={business.from_email}")
        print(f"reply_to_email={business.reply_to_email}")
        print(f"logo_url={business.logo_url}")
        print(f"default_email_text={business.default_email_text}")
        print(f"review_redirect_url={business.review_redirect_url}")
        print(f"timezone={business.timezone}")
        print(f"updated_fields={', '.join(updated_fields)}")


if __name__ == "__main__":
    asyncio.run(main())