from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from loguru import logger

from repositories.feedback_requests import get_feedback_request_by_token
from repositories.businesses import get_business_by_id


async def validate_feedback_token(
    request: Request,
    session: AsyncSession,
    templates: Jinja2Templates,
    token: str,
):
    feedback_request = await get_feedback_request_by_token(
        session=session,
        token=token,
    )

    if feedback_request is None:
        logger.warning(f"Invalid feedback token attempted: {token}")
        return None, templates.TemplateResponse(
            "thank_you.html",
            {
                "request": request,
                "title": "Invalid feedback link",
                "message": "This feedback link is invalid or no longer available.",
                "show_review_link": False,
                "review_url": None,
                "business_name": None,
                "logo_url": None,
            },
            status_code=404,
        )

    if feedback_request.responded_at is not None:
        logger.warning(
            f"Duplicate feedback submission attempted | token={token} | request_id={feedback_request.id}"
        )

        business = await get_business_by_id(session, feedback_request.business_id)

        return None, templates.TemplateResponse(
            "thank_you.html",
            {
                "request": request,
                "title": "Feedback already submitted",
                "message": "Thank you. This feedback link has already been used.",
                "show_review_link": False,
                "review_url": None,
                "business_name": business.name if business else None,
                "logo_url": business.logo_url if business else None,
            },
        )

    return feedback_request, None