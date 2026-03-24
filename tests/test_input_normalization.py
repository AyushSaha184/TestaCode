from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from backend.core.config import Settings
from backend.core.exceptions import AppError
from backend.input.normalizer import normalize_generation_request
from backend.schemas import InputMode, Language


@pytest.mark.asyncio
async def test_normalize_paste_success() -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="paste",
        user_prompt="Generate tests",
        code_content="def add(a, b): return a + b",
        filename=None,
        language="python",
        upload_file=None,
        auto_commit_enabled=None,
    )

    assert request.input_mode == InputMode.paste
    assert request.language == Language.python
    assert warnings == []


@pytest.mark.asyncio
async def test_normalize_paste_autodetects_language_when_omitted() -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="paste",
        user_prompt="Generate tests",
        code_content="const add = (a, b) => a + b;",
        filename=None,
        language=None,
        upload_file=None,
        auto_commit_enabled=None,
    )

    assert request.input_mode == InputMode.paste
    assert request.language == Language.javascript
    assert warnings == []


@pytest.mark.asyncio
async def test_normalize_upload_rejects_unsupported_extension() -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    upload = UploadFile(filename="bad.txt", file=BytesIO(b"hello"))

    with pytest.raises(AppError) as exc_info:
        await normalize_generation_request(
            settings=settings,
            session_id="session-test-1",
            input_mode="upload",
            user_prompt="Generate tests",
            code_content=None,
            filename=None,
            language=None,
            upload_file=upload,
            auto_commit_enabled=None,
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code_content", "expected_language"),
    [
        ("fn main() { println!(\"hello\"); let mut total = 0; }", Language.rust),
        ("package main\nimport (\n  \"fmt\"\n)\nfunc main() { value := 1; fmt.Println(value) }", Language.golang),
        ("using System;\nnamespace Demo { public class Program { static void Main(string[] args) { Console.WriteLine(\"hi\"); } } }", Language.csharp),
    ],
)
async def test_normalize_paste_autodetects_new_languages(code_content: str, expected_language: Language) -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="paste",
        user_prompt="Generate tests",
        code_content=code_content,
        filename=None,
        language=None,
        upload_file=None,
        auto_commit_enabled=None,
    )

    assert request.language == expected_language
    assert warnings == []


@pytest.mark.asyncio
async def test_normalize_prompt_only_defaults_to_python() -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="paste",
        user_prompt="Generate pytest cases for a string parser",
        code_content="",
        filename=None,
        language=None,
        upload_file=None,
        auto_commit_enabled=None,
    )

    assert request.input_mode == InputMode.paste
    assert request.language == Language.python
    assert request.code_content == ""
    assert warnings == []


@pytest.mark.asyncio
async def test_normalize_prompt_only_preserves_explicit_language() -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="paste",
        user_prompt="Generate table-driven tests",
        code_content="",
        filename=None,
        language="golang",
        upload_file=None,
        auto_commit_enabled=None,
    )

    assert request.language == Language.golang
    assert request.code_content == ""
    assert warnings == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content", "expected_language"),
    [
        ("main.rs", b"fn main() { println!(\"ok\"); }", Language.rust),
        ("main.go", b"package main\nfunc main() {}", Language.golang),
        ("Program.cs", b"using System; public class Program {}", Language.csharp),
    ],
)
async def test_normalize_upload_accepts_new_language_extensions(filename: str, content: bytes, expected_language: Language) -> None:
    settings = Settings(database_url="postgresql://example", llm_enabled=False)
    upload = UploadFile(filename=filename, file=BytesIO(content))

    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id="session-test-1",
        input_mode="upload",
        user_prompt="Generate tests",
        code_content=None,
        filename=None,
        language=None,
        upload_file=upload,
        auto_commit_enabled=None,
    )

    assert request.input_mode == InputMode.upload
    assert request.language == expected_language
    assert warnings == []
