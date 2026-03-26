from contextlib import asynccontextmanager

from loguru import logger

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from helpers.auth import COOKIE_NAME

from helpers.db import create_db_and_tables

from routes import pages, feedback, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    logger.info("Database tables ready")
    logger.info(f"BASE_URL: {settings.base_url}")
    logger.info(f"RESEND_API_KEY loaded: {bool(settings.resend_api_key)}")
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    accepts_html = "text/html" in request.headers.get("accept", "")
    is_get_request = request.method == "GET"

    if exc.status_code == 401 and accepts_html and is_get_request:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(COOKIE_NAME)
        return response

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(feedback.router)
app.include_router(auth.router)