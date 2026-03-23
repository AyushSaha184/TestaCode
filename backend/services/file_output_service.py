from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from backend.core.logger import get_logger
from backend.schemas import InputMode, Language, UnifiedContext
from backend.services.supabase_storage_service import SupabaseStorageService

logger = get_logger(__name__)

_SAFE_SEGMENT_RE = re.compile(r"[^a-zA-Z0-9_-]+")
_EXTENSION_MAP: dict[Language, str] = {
    Language.python: "py",
    Language.javascript: "js",
    Language.typescript: "ts",
    Language.java: "java",
}


@dataclass(frozen=True)
class FileOutputResult:
    feature_name: str
    local_test_file_path: str | None
    local_metadata_file_path: str | None
    warnings: list[str]


class FileOutputService:
    def __init__(
        self,
        repository_root: str,
        generated_tests_dir: str,
        storage_service: SupabaseStorageService | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.base_output_dir = (self.repository_root / generated_tests_dir).resolve()
        self.storage_service = storage_service

    def is_storage_configured(self) -> bool:
        return bool(self.storage_service and self.storage_service.is_configured())

    def write_outputs(
        self,
        *,
        job_id: UUID,
        session_id: str,
        input_mode: InputMode,
        original_filename: str | None,
        context: UnifiedContext,
        generated_test_code: str,
        quality_score: int,
        framework_used: str,
        uncovered_areas: list[str],
    ) -> FileOutputResult:
        logger.info("file_output_started", extra={"step": "file_output", "job_id": str(job_id), "status": "processing"})
        feature_name = derive_feature_name(input_mode, original_filename, context)
        ext = _EXTENSION_MAP[context.detected_language]
        safe_session = sanitize_path_segment(session_id) or "unknown_session"
        safe_language = sanitize_path_segment(context.detected_language.value) or "unknown_language"

        target_dir = self.base_output_dir / safe_session / safe_language / feature_name
        target_dir.mkdir(parents=True, exist_ok=True)

        test_file = target_dir / f"test_{feature_name}.{ext}"
        metadata_file = target_dir / f"test_{feature_name}.json"
        warnings: list[str] = []

        metadata_payload: dict[str, Any] = {
            "job_id": str(job_id),
            "session_id": session_id,
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "input_mode": input_mode.value,
            "quality_score": quality_score,
            "framework_used": framework_used,
            "uncovered_areas": uncovered_areas,
            "detected_language": context.detected_language.value,
            "source_filename": original_filename,
        }

        try:
            atomic_write_text(test_file, generated_test_code)
            atomic_write_text(metadata_file, json.dumps(metadata_payload, indent=2))

            logger.info(
                "file_output_completed",
                extra={
                    "step": "file_output",
                    "job_id": str(job_id),
                    "status": "ok",
                },
            )
            return FileOutputResult(
                feature_name=feature_name,
                local_test_file_path=_normalize_slashes(test_file.relative_to(self.repository_root).as_posix()),
                local_metadata_file_path=_normalize_slashes(metadata_file.relative_to(self.repository_root).as_posix()),
                warnings=warnings,
            )
        except Exception:
            logger.exception(
                "file_output_failed",
                extra={"step": "file_output", "job_id": str(job_id), "status": "failed"},
            )
            raise

    def upload_source_file(
        self,
        *,
        session_id: str,
        original_filename: str,
        detected_language: Language,
        source_code: str,
    ) -> tuple[str | None, str | None]:
        if not self.storage_service or not self.storage_service.is_configured():
            return None, None

        safe_session = sanitize_path_segment(session_id) or "unknown_session"
        safe_language = sanitize_path_segment(detected_language.value) or "unknown_language"
        safe_name = sanitize_path_segment(Path(original_filename).stem) or "uploaded_source"
        extension = Path(original_filename).suffix.lower() or f".{_EXTENSION_MAP[detected_language]}"
        object_path = f"uploads/{safe_session}/{safe_language}/{safe_name}{extension}"
        uploaded = self.storage_service.upload_text(
            object_path=object_path,
            content=source_code,
            content_type="text/plain; charset=utf-8",
        )
        return uploaded.object_path, uploaded.url

    def upload_output_artifacts(
        self,
        *,
        session_id: str,
        detected_language: Language,
        feature_name: str,
        generated_test_code: str,
        metadata_payload: dict[str, Any],
    ) -> tuple[str | None, str | None, str | None, str | None, list[str]]:
        if not self.storage_service or not self.storage_service.is_configured():
            return None, None, None, None, []

        safe_session = sanitize_path_segment(session_id) or "unknown_session"
        safe_language = sanitize_path_segment(detected_language.value) or "unknown_language"
        safe_feature = sanitize_path_segment(feature_name) or "generated_feature"
        ext = _EXTENSION_MAP[detected_language]
        storage_base_path = f"sessions/{safe_session}/{safe_language}/{safe_feature}"
        storage_test_path = f"{storage_base_path}/test_{safe_feature}.{ext}"
        storage_metadata_path = f"{storage_base_path}/test_{safe_feature}.json"
        warnings: list[str] = []
        output_test_path: str | None = None
        output_metadata_path: str | None = None
        output_test_url: str | None = None
        output_metadata_url: str | None = None

        try:
            uploaded_test = self.storage_service.upload_text(
                object_path=storage_test_path,
                content=generated_test_code,
                content_type="text/plain; charset=utf-8",
            )
            output_test_path = uploaded_test.object_path
            output_test_url = uploaded_test.url
        except Exception as exc:
            warnings.append(f"Supabase upload failed for test artifact: {exc}")

        try:
            uploaded_metadata = self.storage_service.upload_text(
                object_path=storage_metadata_path,
                content=json.dumps(metadata_payload, indent=2),
                content_type="application/json; charset=utf-8",
            )
            output_metadata_path = uploaded_metadata.object_path
            output_metadata_url = uploaded_metadata.url
        except Exception as exc:
            warnings.append(f"Supabase upload failed for metadata artifact: {exc}")

        return output_test_path, output_metadata_path, output_test_url, output_metadata_url, warnings


def derive_feature_name(input_mode: InputMode, original_filename: str | None, context: UnifiedContext) -> str:
    if input_mode == InputMode.upload and original_filename:
        raw = Path(original_filename).stem
    elif context.function_metadata:
        raw = context.function_metadata[0].name
    else:
        raw = "generated_feature"

    sanitized = sanitize_path_segment(raw)
    return sanitized or "generated_feature"


def sanitize_path_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT_RE.sub("_", value.strip().lower())
    cleaned = cleaned.strip("._-")
    cleaned = cleaned.replace("..", "")
    return cleaned[:80]


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _normalize_slashes(path: str) -> str:
    return path.replace("\\", "/")
