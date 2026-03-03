import os
from fastapi import HTTPException
from backend.input.models import UnifiedContext, ClassifiedIntent
from backend.schemas import InputMode, TargetLanguage
from backend.core.config import logger


# ─── File Size Limit ──────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024  # 50KB

# ─── Extension → Language Mapping ─────────────────────────────────────────────
EXTENSION_LANGUAGE_MAP = {
    ".py": TargetLanguage.python,
    ".js": TargetLanguage.javascript,
    ".jsx": TargetLanguage.javascript,
    ".ts": TargetLanguage.typescript,
    ".tsx": TargetLanguage.typescript,
    ".java": TargetLanguage.java,
}


def process_code_input(
    code_content: str,
    language: TargetLanguage,
    user_prompt: str,
    filename: str | None = None,
) -> UnifiedContext:
    """
    Unified entry point for all code input (paste or upload).
    Validates code, runs parser, runs intent classifier, and assembles
    the UnifiedContext object that the agent layer consumes.
    """
    if not code_content.strip():
        raise HTTPException(status_code=400, detail="Code content cannot be empty.")

    # Enforce file size limit
    if len(code_content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Code content too large. Maximum size is 50KB.")

    # Determine input mode
    input_mode = InputMode.upload if filename else InputMode.paste

    # If filename provided, validate extension and reconcile language
    if filename:
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext not in EXTENSION_LANGUAGE_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Supported: {', '.join(EXTENSION_LANGUAGE_MAP.keys())}",
            )

    warnings = []
    extracted_functions = []

    # ─── Code Parsing ─────────────────────────────────────────────────────────
    if language == TargetLanguage.python:
        from backend.input.parsers import parse_python_code
        try:
            parsed_data = parse_python_code(code_content)
            extracted_functions = parsed_data.get("functions", [])
            warnings.extend(parsed_data.get("warnings", []))
        except SyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Python Syntax Error at line {e.lineno}: {e.msg}. Please fix the code and try again.",
            )
    elif language in (TargetLanguage.javascript, TargetLanguage.typescript):
        # JS/TS parsing will be handled by LLM-based parser in Phase 2
        warnings.append("AST extraction for JS/TS uses LLM-based parsing (Phase 2).")
    elif language == TargetLanguage.java:
        warnings.append("Java code parsing is not yet supported. The LLM will use raw code context.")

    # ─── Prompt Intent Classification ─────────────────────────────────────────
    # Placeholder — full implementation in Phase 2 (intent_classifier.py)
    classified_intent = ClassifiedIntent(
        test_type="unit",
        target_scope="all",
        target_framework="auto",
        confidence=0.5,
    )

    logger.info(
        f"Input processed | mode={input_mode.value} | lang={language.value} "
        f"| functions={len(extracted_functions)} | warnings={len(warnings)}"
    )

    return UnifiedContext(
        raw_code=code_content,
        language=language,
        input_mode=input_mode,
        filename=filename,
        extracted_functions=extracted_functions,
        classified_intent=classified_intent,
        user_prompt=user_prompt,
        warnings=warnings,
    )


# ─── File Upload Handler (used by Streamlit frontend) ─────────────────────────

async def process_file_upload_bytes(
    file_bytes: bytes,
    filename: str,
    user_prompt: str,
) -> UnifiedContext:
    """
    Handles file uploads from the Streamlit frontend.
    Reads bytes, validates extension/size, detects language, then delegates
    to process_code_input for uniform downstream processing.
    """
    # Size check
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50KB.")

    # Decode
    try:
        content_str = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Ensure the file is standard text and not a compiled binary or image.",
        )

    # Detect language from extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in EXTENSION_LANGUAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(EXTENSION_LANGUAGE_MAP.keys())}",
        )
    language = EXTENSION_LANGUAGE_MAP[ext]

    return process_code_input(
        code_content=content_str,
        language=language,
        user_prompt=user_prompt,
        filename=filename,
    )
