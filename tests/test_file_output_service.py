from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.schemas import FunctionMetadata, InputMode, IntentClassification, Language, UnifiedContext
from backend.services.file_output_service import FileOutputService, derive_feature_name, sanitize_path_segment


def _context(language: Language, function_name: str = "compute_total") -> UnifiedContext:
    return UnifiedContext(
        raw_code="def compute_total(a, b): return a + b",
        detected_language=language,
        function_metadata=[FunctionMetadata(name=function_name)],
        classified_intent=IntentClassification(),
        original_prompt="Generate tests",
        warnings=[],
    )


def test_path_sanitization_and_feature_derivation() -> None:
    ctx = _context(Language.python, function_name="DoThing!!")

    assert sanitize_path_segment("../Bad Name*") == "bad_name"
    assert derive_feature_name(InputMode.upload, "Payments.Service.py", ctx) == "payments_service"
    assert derive_feature_name(InputMode.paste, None, ctx) == "dothing"


def test_file_writer_atomic_and_metadata(tmp_path: Path) -> None:
    service = FileOutputService(repository_root=str(tmp_path), generated_tests_dir="generated_tests")
    ctx = _context(Language.python)

    result = service.write_outputs(
        job_id=uuid4(),
        session_id="session-test-1",
        input_mode=InputMode.paste,
        original_filename=None,
        context=ctx,
        generated_test_code="def test_ok():\n    assert True\n",
        quality_score=9,
        framework_used="pytest",
        uncovered_areas=["none"],
    )

    test_file = tmp_path / result.local_test_file_path
    metadata_file = tmp_path / result.local_metadata_file_path

    assert test_file.exists()
    assert metadata_file.exists()
    assert result.test_file_path is None
    assert result.metadata_file_path is None
    assert result.local_test_file_path == "generated_tests/session-test-1/python/compute_total/test_compute_total.py"
    assert result.local_metadata_file_path == "generated_tests/session-test-1/python/compute_total/test_compute_total.json"
    assert any("Supabase storage is not configured" in warning for warning in result.warnings)

    second = service.write_outputs(
        job_id=uuid4(),
        session_id="session-test-1",
        input_mode=InputMode.paste,
        original_filename=None,
        context=ctx,
        generated_test_code="def test_ok2():\n    assert True\n",
        quality_score=8,
        framework_used="pytest",
        uncovered_areas=[],
    )

    assert second.local_test_file_path == result.local_test_file_path
    assert "test_ok2" in (tmp_path / second.local_test_file_path).read_text(encoding="utf-8")


class FakeStorageService:
    def is_configured(self) -> bool:
        return True

    def upload_text(self, *, object_path: str, content: str, content_type: str):
        class _Result:
            def __init__(self, object_path: str):
                self.object_path = object_path
                self.url = f"https://storage.local/{object_path}"

        return _Result(object_path)


def test_file_writer_uploads_storage_when_configured(tmp_path: Path) -> None:
    service = FileOutputService(
        repository_root=str(tmp_path),
        generated_tests_dir="generated_tests",
        storage_service=FakeStorageService(),
    )
    ctx = _context(Language.typescript, function_name="sum_values")

    result = service.write_outputs(
        job_id=uuid4(),
        session_id="session-test-2",
        input_mode=InputMode.paste,
        original_filename=None,
        context=ctx,
        generated_test_code="test('ok', () => expect(true).toBe(true));\n",
        quality_score=8,
        framework_used="jest",
        uncovered_areas=[],
    )

    assert result.test_file_path == "sessions/session-test-2/typescript/sum_values/test_sum_values.ts"
    assert result.metadata_file_path == "sessions/session-test-2/typescript/sum_values/test_sum_values.json"
    assert result.test_file_url == "https://storage.local/sessions/session-test-2/typescript/sum_values/test_sum_values.ts"
    assert result.metadata_file_url == "https://storage.local/sessions/session-test-2/typescript/sum_values/test_sum_values.json"
    assert result.warnings == []
