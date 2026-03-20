from __future__ import annotations

from typing import Any


class DatabaseClient:
	def __init__(self, dsn: str) -> None:
		if not dsn:
			raise ValueError("SUPABASE_DB_URL is required")
		self.dsn = dsn

	def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
		psycopg, dict_row = _load_psycopg()
		with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)
				rows = cur.fetchall()
		return [dict(row) for row in rows]

	def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
		psycopg, dict_row = _load_psycopg()
		with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)
				row = cur.fetchone()
		return dict(row) if row else None

	def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
		psycopg, dict_row = _load_psycopg()
		with psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True) as conn:
			with conn.cursor() as cur:
				cur.execute(query, params)


def _load_psycopg():
	try:
		import psycopg
		from psycopg.rows import dict_row
	except ImportError as exc:
		raise RuntimeError("psycopg is required for database operations") from exc
	return psycopg, dict_row
