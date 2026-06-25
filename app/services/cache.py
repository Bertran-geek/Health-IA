"""Optional Redis cache for AI answers.

Gracefully degrades to a no-op when Redis is disabled or unreachable so the
service keeps working without the cache container.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if not settings.redis_enabled:
        return None
    if _client is None:
        try:
            import redis  # local import keeps it optional

            _client = redis.Redis.from_url(
                settings.redis_url, socket_connect_timeout=2, decode_responses=True
            )
            _client.ping()
            logger.info("Redis cache connected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable, cache disabled: %s", exc)
            _client = None
    return _client


def _key(question: str, language: str) -> str:
    digest = hashlib.sha256(f"{language}:{question}".encode()).hexdigest()
    return f"hcai:answer:{digest}"


def get_cached(question: str, language: str) -> Optional[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    try:
        raw = client.get(_key(question, language))
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def set_cached(question: str, language: str, payload: Dict[str, Any]) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.setex(
            _key(question, language),
            settings.cache_ttl,
            json.dumps(payload, default=str),
        )
    except Exception:  # noqa: BLE001
        pass


def cache_status() -> str:
    if not settings.redis_enabled:
        return "disabled"
    return "connected" if _get_client() else "unreachable"
