from __future__ import annotations

import threading
import time
from typing import Generic, Protocol, TypeVar

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
