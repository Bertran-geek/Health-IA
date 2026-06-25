"""Safe, read-only query execution.

This module is the ONLY place that runs SQL against the database. It enforces:
- validation via the SQL validator (SELECT-only)
- a hard LIMIT cap on returned rows
- a per-statement timeout
- a read-only transaction
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy import text

from app.config import settings
from app.database.connection import get_engine
from app.security.sql_validator import enforce_limit, validate_sql

logger = logging.getLogger(__name__)


class QueryExecutionError(Exception):
    """Raised when a query fails validation or execution."""


def execute_select(sql: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Validate and execute a SELECT query, returning (columns, rows)."""
    # 1) Hard security gate
    validate_sql(sql)

    # 2) Enforce a row cap
    safe_sql = enforce_limit(sql, settings.db_max_rows)

    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Read-only + statement timeout (MySQL specific session settings)
            try:
                conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
                conn.execute(
                    text("SET SESSION MAX_EXECUTION_TIME = :ms"),
                    {"ms": settings.db_query_timeout * 1000},
                )
            except Exception:  # noqa: BLE001 - non-fatal on non-MySQL backends
                pass

            result = conn.execute(text(safe_sql))
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchall()]
    except QueryExecutionError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query execution failed: %s", exc)
        raise QueryExecutionError(f"Query execution failed: {exc}") from exc

    return columns, rows
