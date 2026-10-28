"""Кэш LLM-ответов в Redis: повторный скрининг того же резюме не тратит токены.
Если Redis недоступен — молча работаем без кэша."""

import hashlib
import json
import logging

from app.config import get_settings

log = logging.getLogger(__name__)
_client = None
_disabled = False


def _redis():
    global _client, _disabled
    if _disabled:
        return None
    if _client is None:
        try:
            import redis

            _client = redis.Redis.from_url(get_settings().redis_url, socket_timeout=1, socket_connect_timeout=1)
            _client.ping()
        except Exception as e:  # noqa: BLE001
            log.warning("Redis недоступен, кэш отключён: %s", e)
            _disabled = True
            return None
    return _client


def make_key(*parts: str) -> str:
    return "llm:" + hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def get(key: str) -> dict | None:
    r = _redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def set(key: str, value: dict, ttl: int = 7 * 24 * 3600) -> None:  # noqa: A001
    r = _redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            pass
