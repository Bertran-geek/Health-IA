"""Regression tests for the SQL safety validator.

Run with:  pytest -q
"""
import pytest

from app.security.sql_validator import (
    UnsafeSQLError,
    enforce_limit,
    validate_sql,
)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM campaign",
        "select count(*) from target where vaccinate = 1",
        "WITH x AS (SELECT 1 AS a) SELECT a FROM x",
        "SELECT c.nom FROM campaign c JOIN target t ON t.id_campain = c.id_campaign",
    ],
)
def test_valid_select_passes(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM target",
        "DROP TABLE campaign",
        "UPDATE target SET vaccinate = 1",
        "INSERT INTO target (age) VALUES (5)",
        "ALTER TABLE campaign ADD COLUMN x INT",
        "TRUNCATE TABLE target",
        "SELECT * FROM target; DROP TABLE target",
        "SELECT * FROM target INTO OUTFILE '/tmp/x'",
        "SELECT * FROM target /* sneaky */; DELETE FROM target",
        "SET @x = 1",
        "CALL some_proc()",
        "",
    ],
)
def test_dangerous_sql_rejected(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_comment_stripping_blocks_hidden_payload():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT 1 -- ok\n; DROP TABLE target")


def test_enforce_limit_adds_limit():
    assert enforce_limit("SELECT * FROM target", 100).endswith("LIMIT 100")


def test_enforce_limit_caps_existing():
    out = enforce_limit("SELECT * FROM target LIMIT 99999", 1000)
    assert out.strip().lower().endswith("limit 1000")


def test_enforce_limit_keeps_small_limit():
    out = enforce_limit("SELECT * FROM target LIMIT 10", 1000)
    assert out.strip().lower().endswith("limit 10")
