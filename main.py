import os
from dotenv import load_dotenv
from loguru import logger
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from helpers.email_renderer import render_feedback_email_html
from helpers.email_sender import send_email_with_resend

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
BASE_URL = os.getenv("BASE_URL")

logger.info("Environment variables loaded")
logger.info(f"RESEND_API_KEY loaded: {RESEND_API_KEY is not None}")
logger.info(f"FROM_EMAIL: {FROM_EMAIL}")
logger.info(f"BASE_URL: {BASE_URL}")

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
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
            "feedback_url": "#"
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

    feedback_url = f"{BASE_URL}/feedback/test"

    html = render_feedback_email_html(
        recipient_email=recipientEmail,
        identifier=identifier,
        message=message,
        feedback_url=feedback_url,
    )

    await send_email_with_resend(
        resend_api_key=RESEND_API_KEY,
        from_email=FROM_EMAIL,
        to_email=recipientEmail,
        subject="We’d love your feedback",
        html=html,
    )

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "success_message": f"Feedback request sent to {recipientEmail}",
        }
    )