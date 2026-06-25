"""Turn raw query results into a human-readable answer via the LLM.

Falls back to a deterministic summary if the LLM is unavailable so the API
always returns something useful.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.llm import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = {
    "fr": (
        "Tu es un analyste de santé publique. À partir de la question de "
        "l'utilisateur et des résultats SQL, rédige une réponse claire, "
        "concise et factuelle en FRANÇAIS. Donne les chiffres clés. "
        "N'invente jamais de données. 2-4 phrases maximum."
    ),
    "en": (
        "You are a public-health analyst. Given the user's question and the "
        "SQL results, write a clear, concise, factual answer in ENGLISH. "
        "Include the key numbers. Never invent data. 2-4 sentences maximum."
    ),
}


def _fallback(columns: List[str], rows: List[Dict[str, Any]], language: str) -> str:
    if not rows:
        return (
            "Aucun résultat trouvé." if language == "fr" else "No results found."
        )
    if len(rows) == 1 and len(columns) == 1:
        value = list(rows[0].values())[0]
        if language == "fr":
            return f"Résultat : {value}."
        return f"Result: {value}."
    n = len(rows)
    if language == "fr":
        return f"{n} ligne(s) retournée(s). Colonnes : {', '.join(columns)}."
    return f"{n} row(s) returned. Columns: {', '.join(columns)}."


def format_answer(
    question: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    language: str,
) -> str:
    """Produce a natural-language answer from the query results."""
    # Cap the data sent to the LLM to keep latency and memory low.
    preview = rows[:30]
    data_blob = json.dumps(
        {"columns": columns, "rows": preview}, default=str, ensure_ascii=False
    )

    try:
        llm = get_llm()
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["en"])),
                HumanMessage(
                    content=f"Question: {question}\nResults JSON: {data_blob}\nAnswer:"
                ),
            ]
        )
        answer = str(response.content).strip()
        if answer:
            return answer
    except Exception as exc:  # noqa: BLE001
        logger.warning("Answer formatting via LLM failed, using fallback: %s", exc)

    return _fallback(columns, rows, language)
