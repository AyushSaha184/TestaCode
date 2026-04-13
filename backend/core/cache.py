from __future__ import annotations

import threading
import time
from typing import Generic, Protocol, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class CacheBackend(Protocol[K, V]):
    def get(self, key: K) -> V | None: ...

    def set(self, key: K, value: V) -> None: ...

    def clear_expired(self) -> int: ...

    def size(self) -> int: ...


class TTLCache(Generic[K, V]):
    CLEANUP_INTERVAL_SECONDS = 60
    MAX_SIZE = 1000

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[K, tuple[float, V]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

    def get(self, key: K) -> V | None:
        self._maybe_cleanup()
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
        self._maybe_cleanup()
        expires_at = time.monotonic() + self.ttl_seconds
        with self._lock:
            if len(self._store) >= self.MAX_SIZE:
                self._evict_oldest_unlocked()
            self._store[key] = (expires_at, value)

    def clear_expired(self) -> int:
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_keys = [k for k, (exp, _) in self._store.items() if exp < now]
            for k in expired_keys:
                self._store.pop(k, None)
                removed += 1
        return removed

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def _maybe_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL_SECONDS:
            return
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        self._last_cleanup = now
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True
        )
        self._cleanup_thread.start()

    def _background_cleanup(self) -> None:
        try:
            removed = self.clear_expired()
            if removed > 0:
                time.sleep(0.1)
        except Exception:
            pass

    def _evict_oldest_unlocked(self) -> None:
        if not self._store:
            return
        oldest_key = min(self._store.keys(), key=lambda k: self._store[k][0])
        self._store.pop(oldest_key, None)

    def close(self) -> None:
        self._stop_cleanup.set()
        if self._cleanup_thread is not None:
            self._cleanup_thread.join(timeout=1.0)
        with self._lock:
            self._store.clear()
