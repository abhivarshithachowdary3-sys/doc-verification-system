"""Database connection using SQLModel + SQLite (swap DATABASE_URL for Postgres in production)."""
from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine
from backend.core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

def create_tables():
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
