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

from backend.util.logger import get_logger
from backend.schemas import InputMode, Language, UnifiedContext

logger = get_logger(__name__)

_SAFE_SEGMENT_RE = re.compile(r"[^a-zA-Z0-9_-]+")
_EXTENSION_MAP: dict[Language, str] = {
    Language.python: "py",
    Language.javascript: "js",
    Language.typescript: "ts",
    Language.java: "java",
    Language.rust: "rs",
    Language.golang: "go",
    Language.csharp: "cs",
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
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.base_output_dir = (self.repository_root / generated_tests_dir).resolve()

    def is_storage_configured(self) -> bool:
        return False

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
    replaced = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        replaced = True
    finally:
        if not replaced and os.path.exists(tmp_name):
            os.remove(tmp_name)


def _normalize_slashes(path: str) -> str:
    return path.replace("\\", "/")
