from sqlmodel import SQLModel, Session, create_engine

from models.business import Business
from models.business_user import BusinessUser
from models.feedback_request import FeedbackRequest

DATABASE_URL = "sqlite:///app.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session