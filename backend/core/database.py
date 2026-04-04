from __future__ import annotations

import time
from typing import Any


class DatabaseClient:
	MAX_CONNECT_RETRIES = 3
	CONNECT_RETRY_BACKOFF_SECONDS = 0.25

	def __init__(self, dsn: str) -> None:
		if not dsn:
			raise ValueError("DATABASE_URL is required")
		self.dsn = dsn

	def _connect(self, *, autocommit: bool = False):
		psycopg, dict_row = _load_psycopg()
		last_error: Exception | None = None
		for attempt in range(1, self.MAX_CONNECT_RETRIES + 1):
			try:
				return psycopg.connect(self.dsn, row_factory=dict_row, autocommit=autocommit)
			except psycopg.OperationalError as exc:
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


def _load_psycopg():
	try:
		import psycopg
		from psycopg.rows import dict_row
	except ImportError as exc:
		raise RuntimeError("psycopg is required for database operations") from exc
	return psycopg, dict_row
