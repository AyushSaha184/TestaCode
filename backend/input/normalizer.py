from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from backend.core.config import Settings
from backend.core.exceptions import AppError
from backend.schemas import GenerationRequest, InputMode, Language

_EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.python,
    ".js": Language.javascript,
    ".ts": Language.typescript,
    ".java": Language.java,
    ".rs": Language.rust,
    ".go": Language.golang,
    ".cs": Language.csharp,
}


def _detect_language_from_code(code_content: str) -> Language:
    source = code_content.strip()
    if not source:
        return Language.python

    checks: list[tuple[Language, tuple[str, ...]]] = [
        (
            Language.rust,
            ("fn ", "let mut ", "impl ", "pub struct ", "println!", "use std::"),
        ),
        (
            Language.golang,
            ("package main", "func ", "fmt.Println", ":=", "import (", " struct"),
        ),
        (
            Language.csharp,
            ("using System", "namespace ", "public class ", "Console.WriteLine", "string[] args", "[Test]", "[Fact]"),
        ),
        (
            Language.java,
            ("public class", "System.out.println", "package "),
        ),
        (
            Language.typescript,
            ("interface ", "type ", ": string", ": number", "implements ", "readonly "),
        ),
        (
            Language.javascript,
            ("function ", "const ", "let ", "=>", "console.log"),
        ),
    ]

    best_language = Language.python
    best_score = 0
    for candidate, patterns in checks:
        score = sum(1 for pattern in patterns if pattern in source)
        if score > best_score:
            best_language = candidate
            best_score = score

    if best_score > 0:
        return best_language

    if "public class" in source or "System.out.println" in source or "package " in source:
        return Language.java

    if "interface " in source or "type " in source or ": string" in source or ": number" in source or "implements " in source:
        return Language.typescript

    if "function " in source or "const " in source or "let " in source or "=>" in source or "console.log" in source:
        return Language.javascript

    return Language.python


def sanitize_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    sanitized = Path(filename).name
    return sanitized.replace("..", "")


async def normalize_generation_request(
    settings: Settings,
    session_id: str | None,
    input_mode: str,
    user_prompt: str,
    code_content: str | None,
    filename: str | None,
    language: str | None,
    upload_file: UploadFile | None,
) -> tuple[GenerationRequest, list[str]]:
    warnings: list[str] = []

    if not session_id or not session_id.strip():
        raise AppError("X-Session-Id header is required", status_code=422)

    try:
        parsed_mode = InputMode(input_mode)
    except ValueError as exc:
        raise AppError("input_mode must be one of: paste, upload", status_code=422) from exc

    safe_filename = sanitize_filename(filename)

    if parsed_mode == InputMode.upload:
        if upload_file is None:
            raise AppError("upload_file is required when input_mode=upload", status_code=422)

        safe_filename = sanitize_filename(upload_file.filename) or safe_filename
        if not safe_filename:
            raise AppError("A valid filename is required for upload mode", status_code=422)

        raw = await upload_file.read()
        max_bytes = settings.max_upload_kb * 1024
        if len(raw) > max_bytes:
            raise AppError(f"Uploaded file exceeds {settings.max_upload_kb}KB size limit", status_code=413)

        try:
            normalized_code = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError("Uploaded file must be UTF-8 encoded text", status_code=422) from exc

        suffix = Path(safe_filename).suffix.lower()
        mapped_language = _EXTENSION_MAP.get(suffix)
        if mapped_language is None:
            supported = ", ".join(_EXTENSION_MAP.keys())
            raise AppError(f"Unsupported file extension '{suffix}'. Supported: {supported}", status_code=422)

        detected_language = mapped_language
        if language and language != detected_language.value:
            warnings.append("Provided language differs from extension; extension-derived language was used")
    else:
        normalized_code = (code_content or "").strip()
        prompt_only = not normalized_code and bool(user_prompt.strip())

        if language:
            try:
                detected_language = Language(language)
            except ValueError as exc:
                raise AppError(
                    "language must be one of: python, javascript, typescript, java, rust, golang, csharp",
                    status_code=422,
                ) from exc
        elif prompt_only:
            detected_language = Language.python
        else:
            if not normalized_code:
                raise AppError("code_content is required when input_mode=paste", status_code=422)
            detected_language = _detect_language_from_code(normalized_code)

    request = GenerationRequest(
        session_id=session_id.strip(),
        input_mode=parsed_mode,
        code_content=normalized_code,
        filename=safe_filename,
        language=detected_language,
        user_prompt=user_prompt,
    )
    return request, warnings
