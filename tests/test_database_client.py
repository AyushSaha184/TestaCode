from __future__ import annotations

from backend.core.database import DatabaseClient


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _query, _params):
        return None

    def fetchall(self):
        return [{"value": 1}]

    def fetchone(self):
        return {"value": 1}


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _FakeCursor()


def test_database_client_retries_then_succeeds(monkeypatch) -> None:
    class _FakePsycopg:
        class OperationalError(Exception):
            pass

    state = {"calls": 0}

    def _connect(_dsn, row_factory=None, autocommit=False):
        state["calls"] += 1
        if state["calls"] < 3:
            raise _FakePsycopg.OperationalError("temporary dns issue")
        return _FakeConn()

    _FakePsycopg.connect = _connect

    monkeypatch.setattr(
        "backend.core.database._load_psycopg",
        lambda: (_FakePsycopg, object()),
    )

    db = DatabaseClient("postgresql://example")
    db.execute("select 1")

    assert state["calls"] == 3


def test_database_client_raises_after_retry_limit(monkeypatch) -> None:
    class _FakePsycopg:
        class OperationalError(Exception):
            pass

    state = {"calls": 0}

    def _connect(_dsn, row_factory=None, autocommit=False):
        state["calls"] += 1
        raise _FakePsycopg.OperationalError("persistent dns issue")

    _FakePsycopg.connect = _connect

    monkeypatch.setattr(
        "backend.core.database._load_psycopg",
        lambda: (_FakePsycopg, object()),
    )

    db = DatabaseClient("postgresql://example")

    try:
        db.execute("select 1")
    except _FakePsycopg.OperationalError:
        pass
    else:
        raise AssertionError("Expected OperationalError")

    assert state["calls"] == db.MAX_CONNECT_RETRIES
