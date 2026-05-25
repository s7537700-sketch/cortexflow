"""
CortexFlow Database - SQLAlchemy session and engine management.
"""

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .models import Base

logger = logging.getLogger("cortexflow.storage.db")


class Database:
    """Database connection and session manager."""

    def __init__(self, url: str = "sqlite:///./data/cortexflow.db"):
        self.url = url
        self.engine = None
        self.SessionLocal = None

    def connect(self, **engine_kwargs):
        """Initialize the engine and session factory."""
        # SQLite needs check_same_thread=False for multi-threaded access
        connect_args = {}
        if self.url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine = create_engine(
            self.url,
            connect_args=connect_args,
            pool_pre_ping=True,
            **engine_kwargs,
        )
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
        logger.info(f"Database connected: {self.url}")

    def create_all(self):
        """Create all tables defined in models."""
        if not self.engine:
            self.connect()
        Base.metadata.create_all(bind=self.engine)
        logger.info("All tables created")

    @contextmanager
    def session(self):
        """Provide a transactional session scope."""
        if not self.SessionLocal:
            self.connect()
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_db_instance = None


def init_db(url: str = "sqlite:///./data/cortexflow.db") -> Database:
    """Initialize the global database instance."""
    global _db_instance
    _db_instance = Database(url)
    _db_instance.connect()
    _db_instance.create_all()
    return _db_instance


def get_db() -> Database:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = init_db()
    return _db_instance
