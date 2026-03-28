from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import settings

from helpers.db import get_session
from helpers.feedback_validation import validate_feedback_token
from helpers.datetime_formatter import format_datetime_for_business
from helpers.email_renderer import render_admin_feedback_notification_html
from helpers.email_sender import send_email_with_resend

from repositories.feedback_requests import respond_to_feedback_request
from repositories.businesses import get_business_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/feedback/{token}", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    token: str,
    score: int = Query(..., ge=1, le=10),
    session: AsyncSession = Depends(get_session),
):
    feedback_request, error_response = await validate_feedback_token(
        request=request,
        session=session,
        templates=templates,
        token=token,
    )

    if error_response:
        return error_response

    business = await get_business_by_id(session, feedback_request.business_id)

    logger.info(
        f"Feedback page opened | token={token} | request_id={feedback_request.id}"
    )

    return templates.TemplateResponse(
        "feedback_page.html",
        {
            "request": request,
            "token": token,
            "score": score,
            "business_name": business.name if business else None,
            "logo_url": business.logo_url if business else None,
        },
    )


@router.post("/submit-feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    token: str = Form(...),
    score: int = Form(...),
    comment: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    feedback_request, error_response = await validate_feedback_token(
        request=request,
        session=session,
        templates=templates,
        token=token,
    )

    if error_response:
        return error_response

    feedback_request = await respond_to_feedback_request(
        session=session,
        feedback_request=feedback_request,
        score=score,
        comment=comment,
    )

    logger.info(
        f"Feedback submitted | token={token} | score={score} | request_id={feedback_request.id}"
    )

    business = await get_business_by_id(session, feedback_request.business_id)

    if business and business.reply_to_email:
        admin_html = render_admin_feedback_notification_html(
            identifier=feedback_request.identifier,
            recipient_email=feedback_request.recipient_email,
            rating=feedback_request.rating,
            comment=feedback_request.comment,
            responded_at=format_datetime_for_business(
                feedback_request.responded_at,
                business.timezone if business else "UTC",
            ),
        )

        try:
            await send_email_with_resend(
                resend_api_key=settings.resend_api_key,
                from_email=business.from_email,
                to_email=business.reply_to_email,
                subject=f"New feedback received for {feedback_request.identifier}",
                html=admin_html,
                reply_to_email=business.reply_to_email,
            )
            logger.info(
                f"Admin feedback notification sent | token={token} | to={business.reply_to_email}"
            )
        except Exception as exc:
            logger.exception(
                f"Failed to send admin feedback notification | token={token} | error={exc}"
            )

    review_url = business.review_redirect_url if business else None
    show_review_link = bool(review_url) and score >= 8

    return templates.TemplateResponse(
        "thank_you.html",
        {
            "request": request,
            "title": "Thank you for your feedback",
            "message": "We appreciate you taking the time to share your experience.",
            "show_review_link": show_review_link,
            "review_url": review_url,
            "business_name": business.name if business else None,
            "logo_url": business.logo_url if business else None,
        },
    )