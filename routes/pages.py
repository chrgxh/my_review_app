import os

from loguru import logger

from sqlmodel import Session

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import BASE_URL

from helpers.db import engine
from helpers.feedback_validation import validate_feedback_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    status: str | None = None,
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
        },
    )


@router.get("/preview-email", response_class=HTMLResponse)
async def preview_email(
    request: Request,
    recipientEmail: str = "",
    identifier: str = "",
    message: str = "",
):
    return templates.TemplateResponse(
        "feedback_email.html",
        {
            "request": request,
            "recipient_email": recipientEmail,
            "identifier": identifier,
            "message": message,
            "feedback_url": f"{BASE_URL}/feedback"
        }
    )


@router.get("/feedback/{token}", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    token: str,
    score: int = Query(..., ge=1, le=10),
):
    with Session(engine) as session:

        feedback_request, error_response = validate_feedback_token(
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