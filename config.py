import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

logger.info("Environment variables loaded")
logger.info(f"RESEND_API_KEY loaded: {os.getenv('RESEND_API_KEY') is not None}")
logger.info(f"FROM_EMAIL: {os.getenv('FROM_EMAIL')}")
logger.info(f"BASE_URL: {os.getenv('BASE_URL')}")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
BASE_URL = os.getenv("BASE_URL")