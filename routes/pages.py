from loguru import logger

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from config import settings

from models.business import Business
from models.business_user import BusinessUser

from helpers.db import get_session
from helpers.dependencies import get_current_user, get_current_business
from helpers.feedback_validation import validate_feedback_token

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

    logger.info(
        f"Feedback page opened | token={token} | request_id={feedback_request.id}"
    )

    return templates.TemplateResponse(
        "feedback_page.html",
        {
            "request": request,
            "token": token,
            "score": score,
        },
    )