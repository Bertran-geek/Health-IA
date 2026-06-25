"""SQLAlchemy engine factory with a connection pool.

The engine is created lazily and shared across the application. We keep the pool
small to respect the low-memory constraints (API <= 500 MB RAM).
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        logger.info("Creating SQLAlchemy engine")
        _engine = create_engine(
            settings.db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
            pool_recycle=1800,
            connect_args={"connect_timeout": 10},
            future=True,
        )
    return _engine


def check_database() -> bool:
    """Lightweight connectivity probe used by the health endpoint."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database health check failed: %s", exc)
        return False
