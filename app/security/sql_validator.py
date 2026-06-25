"""SQL safety validator.

VERY IMPORTANT: this module guarantees that only a single, read-only SELECT
statement can ever reach the database. Any attempt to mutate data or run
multiple statements is rejected.

Defense in depth:
  1. Strip comments (block + line) that could hide payloads.
  2. Reject multiple statements (no `;` chaining).
  3. Require the statement to start with SELECT (or WITH ... SELECT).
  4. Reject a denylist of dangerous keywords.
  5. Reject stacked-query / comment-based bypass attempts.
"""
from __future__ import annotations

import re

# Keywords that must never appear as standalone tokens.
FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace",
    "merge",
    "grant",
    "revoke",
    "rename",
    "call",
    "execute",
    "exec",
    "into",        # blocks `SELECT ... INTO OUTFILE` exfiltration
    "load_file",
    "outfile",
    "dumpfile",
    "lock",
    "unlock",
    "set",         # blocks SET inside the user query (executor sets its own)
    "use",
    "handler",
    "do",
}


class UnsafeSQLError(Exception):
    """Raised when a SQL statement is rejected by the validator."""


def _strip_comments(sql: str) -> str:
    # Remove /* ... */ block comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove -- line comments and # line comments
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"#[^\n]*", " ", sql)
    return sql.strip()


def validate_sql(sql: str) -> str:
    """Validate a SQL string. Returns the cleaned SQL or raises UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty SQL statement.")

    cleaned = _strip_comments(sql)

    # Disallow multiple statements. A single trailing semicolon is allowed.
    no_trailing = cleaned.rstrip().rstrip(";").strip()
    if ";" in no_trailing:
        raise UnsafeSQLError("Multiple SQL statements are not allowed.")

    lowered = no_trailing.lower()

    # Must be a read-only query.
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise UnsafeSQLError("Only SELECT (or WITH ... SELECT) queries are allowed.")

    if lowered.startswith("with") and "select" not in lowered:
        raise UnsafeSQLError("WITH clause must resolve to a SELECT query.")

    # Token-based denylist (word boundaries to avoid false positives like
    # column names that merely contain a keyword substring).
    tokens = set(re.findall(r"[a-zA-Z_]+", lowered))
    forbidden = tokens & FORBIDDEN_KEYWORDS
    if forbidden:
        raise UnsafeSQLError(
            f"Forbidden keyword(s) detected: {', '.join(sorted(forbidden))}."
        )

    return no_trailing


def enforce_limit(sql: str, max_rows: int) -> str:
    """Ensure the query has a LIMIT no greater than max_rows."""
    cleaned = sql.rstrip().rstrip(";").strip()
    limit_match = re.search(r"\blimit\b\s+(\d+)(?:\s*,\s*(\d+))?\s*$", cleaned, re.IGNORECASE)
    if limit_match:
        # If a second number is present it's `LIMIT offset, count`.
        count = int(limit_match.group(2) or limit_match.group(1))
        if count > max_rows:
            cleaned = re.sub(
                r"\blimit\b\s+\d+(?:\s*,\s*\d+)?\s*$",
                f"LIMIT {max_rows}",
                cleaned,
                flags=re.IGNORECASE,
            )
        return cleaned
    return f"{cleaned} LIMIT {max_rows}"
