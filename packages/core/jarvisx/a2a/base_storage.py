from __future__ import annotations

import logging
from typing import Callable, TypeVar, ParamSpec
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as DBSession, DeclarativeBase

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class Base(DeclarativeBase):
    pass


class BaseDatabaseStorageService:
    
    def __init__(self, db_url: str, schema: str = "jarvisx", workspace_id: str = "default", tenant_id: str = "default"):
        sync_url = db_url.replace("+asyncpg", "+psycopg2")
        self.engine = create_engine(sync_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.schema = schema
        self.workspace_id = workspace_id
        self.tenant_id = tenant_id
        
        self._initialize_schema()
        self._log_initialization(sync_url)
    
    def _initialize_schema(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}"))
            conn.commit()
    
    def _log_initialization(self, db_url: str) -> None:
        masked_url = db_url.split('@')[-1] if '@' in db_url else db_url
        service_name = self.__class__.__name__
        logger.info(f"{service_name} initialized with database: {masked_url}, schema: {self.schema}, tenant_id: {self.tenant_id}, workspace_id: {self.workspace_id}")
    
    @contextmanager
    def get_session(self):
        db: DBSession = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def execute_with_session(self, operation: Callable[[DBSession], R]) -> R:
        with self.get_session() as db:
            try:
                result = operation(db)
                db.commit()
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Database operation failed: {e}", exc_info=True)
                raise


__all__ = ["Base", "BaseDatabaseStorageService"]
