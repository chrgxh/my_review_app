import httpx
import secrets

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import settings

from models.business import Business
from models.business_user import BusinessUser
from helpers.dependencies import get_current_user, get_current_business

from helpers.db import get_session
from helpers.feedback_validation import validate_feedback_token
from helpers.datetime_formatter import format_datetime_for_business
from helpers.email_renderer import (
    render_feedback_email_html,
    render_admin_feedback_notification_html,
)
from helpers.email_sender import send_email_with_resend

from repositories.feedback_requests import (
    create_feedback_request,
    respond_to_feedback_request,
)
from repositories.businesses import get_business_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/request-feedback")
async def request_feedback_get():
    return RedirectResponse(url="/", status_code=303)

@router.post("/request-feedback", response_class=HTMLResponse)
async def request_feedback(
    request: Request,
    recipientEmail: str = Form(...),
    identifier: str = Form(...),
    message: str = Form(""),
    session: AsyncSession = Depends(get_session),
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    logger.info(f"Preparing feedback request for {recipientEmail}")

    if current_user.id is None or current_business.id is None:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "error_message": "User or business is not configured correctly.",
            },
            status_code=500,
        )

    current_user_id = current_user.id
    current_business_id = current_business.id
    current_business_from_email = current_business.from_email
    current_business_reply_to_email = current_business.reply_to_email
    current_business_default_email_text = current_business.default_email_text
    current_business_name = current_business.name
    current_business_logo_url = current_business.logo_url

    token = secrets.token_urlsafe(24)
    feedback_url = f"{settings.base_url}/feedback"

    final_message = (
        message.strip()
        if message.strip()
        else (current_business_default_email_text or "")
    )

    html = render_feedback_email_html(
        recipient_email=recipientEmail,
        identifier=identifier,
        message=final_message,
        default_email_text=current_business_default_email_text,
        feedback_url=feedback_url,
        token=token,
        business_name=current_business_name,
        logo_url=current_business_logo_url,
    )

    try:
        resend_data = await send_email_with_resend(
            resend_api_key=settings.resend_api_key,
            from_email=current_business_from_email,
            to_email=recipientEmail,
            subject="We’d love your feedback",
            html=html,
            reply_to_email=current_business_reply_to_email,
        )

        await create_feedback_request(
            session=session,
            business_id=current_business_id,
            sent_by_user_id=current_user_id,
            recipient_email=recipientEmail,
            identifier=identifier,
            message=final_message or None,
            token=token,
            email_provider_id=resend_data.get("id"),
        )

        logger.info(
            f"Feedback email sent | recipient={recipientEmail} | identifier={identifier} | token={token} | business_id={current_business_id} | user_id={current_user_id}"
        )

        return RedirectResponse(url="/?status=success", status_code=303)

    except httpx.HTTPStatusError as exc:
        logger.error(f"Resend rejected the request: {exc.response.text}")
        return RedirectResponse(url="/?status=mail_error", status_code=303)

    except Exception as exc:
        logger.exception(f"Unexpected error while sending email: {exc}")
        return RedirectResponse(url="/?status=server_error", status_code=303)


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
        },
    )