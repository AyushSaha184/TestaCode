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


def test_file_writer_reports_storage_not_configured() -> None:
    service = FileOutputService(
        repository_root=".",
        generated_tests_dir="generated_tests",
    )
    assert service.is_storage_configured() is False


def test_file_writer_uses_new_language_extension() -> None:
    root = (Path("generated_tests") / f"pytest_rust_case_{uuid4().hex}").resolve()
    root.mkdir(parents=True, exist_ok=True)
    service = FileOutputService(repository_root=str(root), generated_tests_dir="generated_tests")
    ctx = _context(Language.rust, function_name="compute_total")

    result = service.write_outputs(
        job_id=uuid4(),
        session_id="session-test-3",
        input_mode=InputMode.paste,
        original_filename=None,
        context=ctx,
        generated_test_code="#[test]\nfn compute_total_works() { assert!(true); }\n",
        quality_score=8,
        framework_used="cargo test",
        uncovered_areas=[],
    )

    assert result.local_test_file_path == "generated_tests/session-test-3/rust/compute_total/test_compute_total.rs"
