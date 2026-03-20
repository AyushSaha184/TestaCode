from __future__ import annotations

import httpx

from backend.services.supabase_storage_service import SupabaseStorageService


class FakeResponse:
    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url))
        if "/object/sign/" in url:
            return FakeResponse({"signedURL": "/storage/v1/object/sign/code-files/sessions/s1/python/f/test_f.py?token=abc"})
        return FakeResponse({})


def test_upload_uses_storage_api_and_returns_signed_url(monkeypatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)

    service = SupabaseStorageService(
        supabase_url="https://project.supabase.co",
        service_role_key="service-role",
        bucket="code-files",
        public_bucket=False,
        signed_url_ttl_seconds=600,
    )

    result = service.upload_text(
        object_path="sessions/s1/python/f/test_f.py",
        content="print('ok')",
        content_type="text/plain; charset=utf-8",
    )

    assert result.object_path == "sessions/s1/python/f/test_f.py"
    assert result.url is not None
    assert result.url.startswith("https://project.supabase.co/storage/v1/object/sign/code-files")
    assert any("/storage/v1/object/code-files/sessions/s1/python/f/test_f.py" in call[1] for call in fake_client.calls)


def test_public_bucket_url_resolution() -> None:
    service = SupabaseStorageService(
        supabase_url="https://project.supabase.co",
        service_role_key="service-role",
        bucket="code-files",
        public_bucket=True,
        signed_url_ttl_seconds=600,
    )

    url = service.resolve_object_url("sessions/s1/python/f/test_f.py")

    assert url == "https://project.supabase.co/storage/v1/object/public/code-files/sessions/s1/python/f/test_f.py"
