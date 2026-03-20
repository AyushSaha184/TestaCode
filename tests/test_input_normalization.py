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
