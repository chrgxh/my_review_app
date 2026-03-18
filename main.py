from contextlib import asynccontextmanager
import os

from loguru import logger

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from helpers.db import create_db_and_tables

from routes import pages, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logger.info("Database tables ready")
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(feedback.router)