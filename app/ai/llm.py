"""LLM client wrapper around Groq (free online AI).

Uses the langchain-groq integration with a low temperature for deterministic SQL.
Get your free API key at https://console.groq.com/keys
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_llm() -> ChatGroq:
    """Return a cached ChatGroq client."""
    logger.info(
        "Initialising Groq LLM model=%s",
        settings.groq_model,
    )
    return ChatGroq(
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=4096,
        timeout=settings.llm_timeout,
        api_key=settings.groq_api_key,
    )


def llm_available() -> bool:
    """Check if the Groq API key is configured."""
    if not settings.groq_api_key or settings.groq_api_key == "your-groq-api-key-here":
        logger.warning("Groq API key not configured")
        return False
    return True
