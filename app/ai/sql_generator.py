"""Natural language -> SQL generation using the LLM grounded on the schema."""
from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.llm import get_llm
from app.database.schema_reader import build_schema_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert MySQL data analyst for a health campaign
management system. Convert the user's question into ONE valid MySQL SELECT query.

STRICT RULES:
- Output ONLY the SQL query. No explanation, no markdown fences, no comments.
- The query MUST be a single read-only SELECT statement.
- NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any
  data-modifying statement.
- Always add a sensible LIMIT (<= 1000) unless the query is an aggregate that
  returns few rows.
- Use the exact table and column names from the provided schema.
- Use proper JOINs following the foreign keys described in the schema.
- For coverage/percentage use ROUND(SUM(vaccinate)/COUNT(id_target)*100, 1).
- When filtering by a region/department/CHW name, match with the name column
  using a case-insensitive LIKE or =.
- Prefer aggregates (COUNT, SUM, AVG, GROUP BY) when the question asks for
  numbers, rankings, coverage, or "par/per" breakdowns.

{schema_context}
"""


def _clean_sql(raw: str) -> str:
    """Strip markdown fences / prose the model may wrap around the SQL."""
    text = raw.strip()
    # Remove ```sql ... ``` fences
    fence = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    # If model added prose, keep from the first SELECT/WITH onward.
    match = re.search(r"\b(select|with)\b", text, re.IGNORECASE)
    if match:
        text = text[match.start():]
    # Keep a single statement.
    text = text.split(";")[0].strip()
    return text


def generate_sql(question: str) -> str:
    """Generate a SQL query for the given natural-language question."""
    schema_context = build_schema_context()
    system = SYSTEM_PROMPT.format(schema_context=schema_context)

    llm = get_llm()
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=f"Question: {question}\nSQL:"),
        ]
    )
    sql = _clean_sql(str(response.content))
    logger.info("Generated SQL: %s", sql)
    return sql
