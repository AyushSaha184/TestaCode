from __future__ import annotations

import pickle
import threading
import time
from typing import Generic, Protocol, TypeVar

from backend.util.logger import get_logger

logger = get_logger(__name__)

K = TypeVar("K")
V = TypeVar("V")


class CacheBackend(Protocol[K, V]):
    def get(self, key: K) -> V | None:
        ...

    def set(self, key: K, value: V) -> None:
        ...


class TTLCache(Generic[K, V]):
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[K, tuple[float, V]] = {}
        self._lock = threading.Lock()

    def get(self, key: K) -> V | None:
        now = time.monotonic()
        with self._lock:
            payload = self._store.get(key)
            if payload is None:
                return None
            expires_at, value = payload
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: K, value: V) -> None:
        expires_at = time.monotonic() + self.ttl_seconds
        with self._lock:
            self._store[key] = (expires_at, value)


class RedisTTLCache(Generic[V]):
    def __init__(self, redis_client, ttl_seconds: int, key_prefix: str) -> None:
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix.strip()

    def _key(self, key: str) -> str:
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def get(self, key: str) -> V | None:
        raw = self.redis_client.get(self._key(key))
        if raw is None:
            return None
        try:
            return pickle.loads(raw)
        except Exception:
            logger.warning("redis_cache_deserialize_failed", extra={"step": "cache", "status": "failed"})
            return None

    def set(self, key: str, value: V) -> None:
        payload = pickle.dumps(value)
        self.redis_client.setex(self._key(key), self.ttl_seconds, payload)
