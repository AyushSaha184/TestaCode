from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any


class DatabaseClient:
	MAX_CONNECT_RETRIES = 3
	CONNECT_RETRY_BACKOFF_SECONDS = 0.25

	def __init__(self, dsn: str) -> None:
		if not dsn:
			raise ValueError("DATABASE_URL is required")
		self.dsn = dsn
		self._psycopg, self._dict_row = _load_psycopg()
		self._pool = _load_connection_pool(self.dsn, self._dict_row)

	@contextmanager
	def _connect(self, *, autocommit: bool = False):
		if self._pool is not None:
			with self._pool.connection() as conn:
				conn.autocommit = autocommit
				yield conn
			return

		last_error: Exception | None = None
		for attempt in range(1, self.MAX_CONNECT_RETRIES + 1):
			try:
				with self._psycopg.connect(self.dsn, row_factory=self._dict_row, autocommit=autocommit) as conn:
					yield conn
					return
			except self._psycopg.OperationalError as exc:
				last_error = exc
				if attempt < self.MAX_CONNECT_RETRIES:
					time.sleep(self.CONNECT_RETRY_BACKOFF_SECONDS * attempt)

		if last_error is not None:
			raise last_error
		raise RuntimeError("Failed to open database connection")

	def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)
				rows = cur.fetchall()
		return [dict(row) for row in rows]

	def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)
				row = cur.fetchone()
		return dict(row) if row else None

	def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
		with self._connect(autocommit=True) as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)

	def close(self) -> None:
		if self._pool is not None:
			self._pool.close()


def _load_psycopg():
	try:
		import psycopg
		from psycopg.rows import dict_row
	except ImportError as exc:
		raise RuntimeError("psycopg is required for database operations") from exc
	return psycopg, dict_row


def _load_connection_pool(dsn: str, dict_row):
	try:
		from psycopg_pool import ConnectionPool
	except ImportError:
		return None

	try:
		pool = ConnectionPool(
			conninfo=dsn,
			min_size=1,
			max_size=10,
			kwargs={"row_factory": dict_row},
			open=False,
		)
		pool.open(wait=True)
		return pool
	except Exception:
		return None
