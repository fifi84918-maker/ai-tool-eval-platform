"""Database configuration and session management."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base class for all models
Base = declarative_base()

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://skilleval:skilleval_dev_pass@localhost:5432/skilleval_db",
)

# Create engine (pool settings for production should be tuned)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL logging during development
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Initialize database (create all tables).
    
    For production, use Alembic migrations instead.
    This is useful for tests and local development.
    """
    Base.metadata.create_all(bind=engine)
