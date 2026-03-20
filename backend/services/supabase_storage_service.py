from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class StorageArtifactUploadResult:
    object_path: str
    url: str | None


class SupabaseStorageService:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        bucket: str,
        public_bucket: bool,
        signed_url_ttl_seconds: int,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket
        self.public_bucket = public_bucket
        self.signed_url_ttl_seconds = signed_url_ttl_seconds

    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.service_role_key and self.bucket)

    def upload_text(self, *, object_path: str, content: str, content_type: str) -> StorageArtifactUploadResult:
        if not self.is_configured():
            raise ValueError("Supabase storage is not configured")

        encoded_path = quote(object_path, safe="/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, headers=headers, content=content.encode("utf-8"))
            response.raise_for_status()

        return StorageArtifactUploadResult(object_path=object_path, url=self.resolve_object_url(object_path))

    def resolve_object_url(self, object_path: str) -> str | None:
        if not object_path:
            return None
        if self.public_bucket:
            return self.build_public_url(object_path)
        return self.build_signed_url(object_path, expires_in=self.signed_url_ttl_seconds)

    def build_public_url(self, object_path: str) -> str:
        encoded_path = quote(object_path, safe="/")
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{encoded_path}"

    def build_signed_url(self, object_path: str, *, expires_in: int) -> str | None:
        if not self.is_configured():
            return None

        encoded_path = quote(object_path, safe="/")
        sign_url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{encoded_path}"
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=20.0) as client:
            response = client.post(sign_url, headers=headers, json={"expiresIn": int(expires_in)})
            response.raise_for_status()
            payload = response.json()

        tokenized_path = payload.get("signedURL")
        if not tokenized_path:
            return None
        if tokenized_path.startswith("http"):
            return tokenized_path
        return f"{self.supabase_url}{tokenized_path}"
