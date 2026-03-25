from contextlib import asynccontextmanager

from loguru import logger

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings

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

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(feedback.router)
app.include_router(auth.router)