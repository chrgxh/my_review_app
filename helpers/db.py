from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from models.business import Business
from models.business_user import BusinessUser
from models.feedback_request import FeedbackRequest

DATABASE_URL = "sqlite+aiosqlite:///app.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with AsyncSession(engine) as session:
        yield session