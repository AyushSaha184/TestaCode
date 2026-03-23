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


def test_file_writer_atomic_and_metadata() -> None:
    root = (Path("generated_tests") / f"pytest_atomic_case_{uuid4().hex}").resolve()
    root.mkdir(parents=True, exist_ok=True)
    service = FileOutputService(repository_root=str(root), generated_tests_dir="generated_tests")
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

    test_file = (root / result.local_test_file_path).resolve()
    metadata_file = (root / result.local_metadata_file_path).resolve()

    assert test_file.exists()
    assert metadata_file.exists()
    assert result.local_test_file_path == "generated_tests/session-test-1/python/compute_total/test_compute_total.py"
    assert result.local_metadata_file_path == "generated_tests/session-test-1/python/compute_total/test_compute_total.json"
    assert result.warnings == []

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
    assert "test_ok2" in (root / second.local_test_file_path).resolve().read_text(encoding="utf-8")


class FakeStorageService:
    def is_configured(self) -> bool:
        return True

    def upload_text(self, *, object_path: str, content: str, content_type: str):
        class _Result:
            def __init__(self, object_path: str):
                self.object_path = object_path
                self.url = f"https://storage.local/{object_path}"

        return _Result(object_path)


def test_file_writer_uploads_storage_when_configured() -> None:
    service = FileOutputService(
        repository_root=".",
        generated_tests_dir="generated_tests",
        storage_service=FakeStorageService(),
    )

    test_path, metadata_path, test_url, metadata_url, warnings = service.upload_output_artifacts(
        session_id="session-test-2",
        detected_language=Language.typescript,
        feature_name="sum_values",
        generated_test_code="test('ok', () => expect(true).toBe(true));\n",
        metadata_payload={"job_id": "123"},
    )

    assert test_path == "sessions/session-test-2/typescript/sum_values/test_sum_values.ts"
    assert metadata_path == "sessions/session-test-2/typescript/sum_values/test_sum_values.json"
    assert test_url == "https://storage.local/sessions/session-test-2/typescript/sum_values/test_sum_values.ts"
    assert metadata_url == "https://storage.local/sessions/session-test-2/typescript/sum_values/test_sum_values.json"
    assert warnings == []
