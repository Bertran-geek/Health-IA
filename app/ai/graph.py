"""LangGraph workflow orchestrating the NL->SQL->answer pipeline.

Flow:
    question
       -> generate_sql
       -> validate_sql        (retry generation once on failure)
       -> execute
       -> format_answer + analytics (chart + trend)

State is a TypedDict passed between nodes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.ai.answer_formatter import format_answer
from app.ai.sql_generator import generate_sql
from app.database.executor import QueryExecutionError, execute_select
from app.security.sql_validator import UnsafeSQLError, validate_sql
from app.services.analytics import build_chart, describe_trend

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    question: str
    language: str
    include_chart: bool
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    answer: str
    chart: Optional[dict]
    trend: Optional[str]
    error: Optional[str]
    attempts: int


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #
def node_generate_sql(state: PipelineState) -> PipelineState:
    state["attempts"] = state.get("attempts", 0) + 1
    state["sql"] = generate_sql(state["question"])
    return state


def node_validate(state: PipelineState) -> PipelineState:
    try:
        state["sql"] = validate_sql(state["sql"])
        state["error"] = None
    except UnsafeSQLError as exc:
        state["error"] = f"unsafe_sql: {exc}"
    return state


def node_execute(state: PipelineState) -> PipelineState:
    try:
        columns, rows = execute_select(state["sql"])
        state["columns"] = columns
        state["rows"] = rows
        state["error"] = None
    except (QueryExecutionError, UnsafeSQLError) as exc:
        state["error"] = f"execution_error: {exc}"
    return state


def node_respond(state: PipelineState) -> PipelineState:
    columns = state.get("columns", [])
    rows = state.get("rows", [])
    language = state.get("language", "en")

    state["answer"] = format_answer(state["question"], columns, rows, language)

    if state.get("include_chart", True):
        state["chart"] = build_chart(columns, rows)
        state["trend"] = describe_trend(columns, rows, language)
    else:
        state["chart"] = None
        state["trend"] = None
    return state


def node_fail(state: PipelineState) -> PipelineState:
    language = state.get("language", "en")
    msg = state.get("error", "unknown error")
    if language == "fr":
        state["answer"] = (
            "Je n'ai pas pu produire une requête sûre pour cette question. "
            f"Détail technique : {msg}"
        )
    else:
        state["answer"] = (
            "I could not produce a safe query for this question. "
            f"Technical detail: {msg}"
        )
    state.setdefault("columns", [])
    state.setdefault("rows", [])
    state["chart"] = None
    state["trend"] = None
    return state


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def route_after_validate(state: PipelineState) -> str:
    if not state.get("error"):
        return "execute"
    # Retry generation once, then fail.
    if state.get("attempts", 1) < 2:
        return "generate_sql"
    return "fail"


def route_after_execute(state: PipelineState) -> str:
    if not state.get("error"):
        return "respond"
    if state.get("attempts", 1) < 2:
        return "generate_sql"
    return "fail"


# --------------------------------------------------------------------------- #
# Graph assembly (compiled once)
# --------------------------------------------------------------------------- #
def _build_graph():
    g = StateGraph(PipelineState)
    g.add_node("generate_sql", node_generate_sql)
    g.add_node("validate", node_validate)
    g.add_node("execute", node_execute)
    g.add_node("respond", node_respond)
    g.add_node("fail", node_fail)

    g.set_entry_point("generate_sql")
    g.add_edge("generate_sql", "validate")
    g.add_conditional_edges(
        "validate",
        route_after_validate,
        {"execute": "execute", "generate_sql": "generate_sql", "fail": "fail"},
    )
    g.add_conditional_edges(
        "execute",
        route_after_execute,
        {"respond": "respond", "generate_sql": "generate_sql", "fail": "fail"},
    )
    g.add_edge("respond", END)
    g.add_edge("fail", END)
    return g.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def run_pipeline(
    question: str, language: str, include_chart: bool = True
) -> PipelineState:
    """Execute the full pipeline for a single question."""
    initial: PipelineState = {
        "question": question,
        "language": language,
        "include_chart": include_chart,
        "attempts": 0,
    }
    result = get_graph().invoke(initial)
    return result  # type: ignore[return-value]
