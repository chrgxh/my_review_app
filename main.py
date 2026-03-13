import os
from dotenv import load_dotenv
from loguru import logger
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
        }
    )