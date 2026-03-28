import httpx
import secrets
from loguru import logger

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from config import settings

from models.business import Business
from models.business_user import BusinessUser
from helpers.dependencies import get_current_user, get_current_business

from helpers.db import get_session
from helpers.dependencies import get_current_user, get_current_business
from helpers.email_renderer import render_feedback_email_html
from helpers.email_sender import send_email_with_resend

from repositories.feedback_requests import create_feedback_request

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    status: str | None = None,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    success_message = None
    error_message = None

    if status == "success":
        success_message = "Feedback request sent successfully."
    elif status == "mail_error":
        error_message = "Email could not be sent. Please check the recipient address or email configuration."
    elif status == "server_error":
        error_message = "Unexpected error while sending the email."

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "success_message": success_message,
            "error_message": error_message,
            "current_user": current_user,
            "current_business": current_business,
        },
    )


@router.get("/preview-email", response_class=HTMLResponse)
async def preview_email(
    request: Request,
    recipientEmail: str = "",
    identifier: str = "",
    message: str = "",
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    return templates.TemplateResponse(
        "feedback_email.html",
        {
            "request": request,
            "recipient_email": recipientEmail,
            "identifier": identifier,
            "message": message,
            "default_email_text": current_business.default_email_text,
            "feedback_url": f"{settings.base_url}/feedback",
            "current_user": current_user,
            "current_business": current_business,
            "business_name": current_business.name,
            "logo_url": current_business.logo_url,
        },
    )

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
