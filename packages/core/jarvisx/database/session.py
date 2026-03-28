from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from jarvisx.config.configs import BASE_DB_URL_SYNC, POSTGRES_SCHEMA

engine = create_engine(BASE_DB_URL_SYNC)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_engine():
    return engine


def get_db():
    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {POSTGRES_SCHEMA}"))
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {POSTGRES_SCHEMA}"))
        yield db
    finally:
        db.close()
