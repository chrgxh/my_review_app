import os
import httpx
import secrets
from dotenv import load_dotenv
from loguru import logger

from sqlmodel import Session, select

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from contextlib import asynccontextmanager

from models.business import Business
from models.business_user import BusinessUser
from models.feedback_request import FeedbackRequest

from helpers.email_renderer import render_feedback_email_html
from helpers.email_sender import send_email_with_resend
from helpers.db import create_db_and_tables, engine
from helpers.feedback_validation import validate_feedback_token

from repositories.feedback_requests import (
    create_feedback_request,
    get_feedback_request_by_token,
    respond_to_feedback_request,
)
from repositories.businesses import get_business_by_id

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
BASE_URL = os.getenv("BASE_URL")

logger.info("Environment variables loaded")
logger.info(f"RESEND_API_KEY loaded: {RESEND_API_KEY is not None}")
logger.info(f"FROM_EMAIL: {FROM_EMAIL}")
logger.info(f"BASE_URL: {BASE_URL}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logger.info("Database tables ready")
    yield

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
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

@app.get("/preview-email", response_class=HTMLResponse)
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

@app.post("/request-feedback", response_class=HTMLResponse)
async def request_feedback(
    request: Request,
    recipientEmail: str = Form(...),
    identifier: str = Form(...),
    message: str = Form(""),
):
    logger.info(f"Preparing feedback request for {recipientEmail}")

    with Session(engine) as session:
        business = session.exec(select(Business).order_by(Business.id)).first()
        user = session.exec(select(BusinessUser).order_by(BusinessUser.id)).first()

        if business is None or user is None:
            return templates.TemplateResponse(
                "admin.html",
                {
                    "request": request,
                    "error_message": "No business or business user found. Run the seed script first.",
                },
            )

        token = secrets.token_urlsafe(24)
        feedback_url = f"{BASE_URL}/feedback"

        final_message = message.strip() if message.strip() else (business.default_email_text or "")

        html = render_feedback_email_html(
            recipient_email=recipientEmail,
            identifier=identifier,
            message=final_message,
            feedback_url=feedback_url,
            token=token,
        )

        try:
            resend_data = await send_email_with_resend(
                resend_api_key=RESEND_API_KEY,
                from_email=business.from_email,
                to_email=recipientEmail,
                subject="We’d love your feedback",
                html=html,
                reply_to_email=business.reply_to_email,
            )

            create_feedback_request(
                session=session,
                business_id=business.id,
                sent_by_user_id=user.id,
                recipient_email=recipientEmail,
                identifier=identifier,
                message=final_message or None,
                token=token,
                email_provider_id=resend_data.get("id"),
            )

            logger.info(
                f"Feedback email sent | recipient={recipientEmail} | identifier={identifier} | token={token}"
            )

            return RedirectResponse(url="/?status=success", status_code=303)

        except httpx.HTTPStatusError as exc:
            logger.error(f"Resend rejected the request: {exc.response.text}")

            return RedirectResponse(url="/?status=mail_error", status_code=303)

        except Exception as exc:
            logger.exception(f"Unexpected error while sending email: {exc}")

            return RedirectResponse(url="/?status=server_error", status_code=303)

@app.get("/feedback/{token}", response_class=HTMLResponse)
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

@app.post("/submit-feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    token: str = Form(...),
    score: int = Form(...),
    comment: str = Form(""),
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

        feedback_request = respond_to_feedback_request(
            session=session,
            feedback_request=feedback_request,
            score=score,
            comment=comment,
        )

        logger.info(
            f"Feedback submitted | token={token} | score={score} | request_id={feedback_request.id}"
        )

        business = get_business_by_id(session, feedback_request.business_id)

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