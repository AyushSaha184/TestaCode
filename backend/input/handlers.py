from fastapi import HTTPException
from backend.input.models import UnifiedInput
from backend.schemas import InputMode, TargetLanguage
import re

def process_natural_language(text_input: str, target_lang: TargetLanguage) -> UnifiedInput:
    """
    Validates and standardizes natural language feature requests.
    Flags overly vague or short descriptions.
    """
    cleaned_text = text_input.strip()
    
    # Word count heuristic
    words = cleaned_text.split()
    if len(words) < 5:
        raise HTTPException(
            status_code=400, 
            detail="The description is too short. Please provide at least a full sentence describing the expected behavior."
        )

    warnings = []
    
    # Simple vagueness check (no actionable nouns/verbs typical to testing)
    test_keywords = r'(function|class|method|api|endpoint|return|fail|exception|error|parameter|input|output|should|must|validate)'
    if not re.search(test_keywords, cleaned_text, re.IGNORECASE):
        warnings.append("Vague description detected. The AI may require clarification to generate accurate edge cases.")
        
    return UnifiedInput(
        raw_content=cleaned_text,
        mode=InputMode.natural_language,
        language=target_lang,
        extracted_functions=[],
        warnings=warnings
    )

def process_pasted_code(code_str: str, target_lang: TargetLanguage) -> UnifiedInput:
    """
    Validates pasted code and runs it through the AST parser if Python.
    """
    if not code_str.strip():
        raise HTTPException(status_code=400, detail="Pasted code cannot be empty.")
        
    warnings = []
    extracted_functions = []
    
    if target_lang == TargetLanguage.python:
        from backend.input.parsers import parse_python_code
        try:
            parsed_data = parse_python_code(code_str)
            extracted_functions = parsed_data.get("functions", [])
            warnings.extend(parsed_data.get("warnings", []))
        except SyntaxError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Python Syntax Error in pasted code at line {e.lineno}: {e.msg}. Please fix the code and try again."
            )
    else:
        # JavaScript/TypeScript placeholder (Would use external JS parser eventually)
        warnings.append("AST extraction for JavaScript is not yet fully supported. The LLM will use raw code context only.")

    return UnifiedInput(
        raw_content=code_str,
        mode=InputMode.pasted_code,
        language=target_lang,
        extracted_functions=extracted_functions,
        warnings=warnings
    )

import os
from fastapi import UploadFile

MAX_FILE_SIZE_BYTES = 50 * 1024 # 50KB

async def process_file_upload(file: UploadFile) -> UnifiedInput:
    """
    Reads an uploaded file stream, validates its extension/size, 
    detects language, and passes it through AST if Python.
    """
    # Extension validation
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    
    if ext == ".py":
        language = TargetLanguage.python
    elif ext in [".js", ".ts"]:
        language = TargetLanguage.javascript
    else:
        from backend.core.config import logger
        logger.warning(f"Rejected file with invalid extension: {ext}")
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Please upload .py, .js, or .ts files.")

    # Size Verification & Decoding
    content_bytes = await file.read()
    
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        from backend.core.config import logger
        logger.warning(f"Rejected file over size limit: {len(content_bytes)} bytes")
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50KB.")

    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        from backend.core.config import logger
        logger.warning("Rejected file - failed UTF-8 decode (possible binary).")
        raise HTTPException(status_code=400, detail="Ensure the file is standard text and not a compiled binary or image.")

    warnings = []
    extracted_functions = []

    # Parse if Python
    if language == TargetLanguage.python:
        try:
            from backend.input.parsers import parse_python_code
            parsed_data = parse_python_code(content_str)
            extracted_functions = parsed_data.get("functions", [])
            warnings.extend(parsed_data.get("warnings", []))
        except SyntaxError as e:
            raise HTTPException(status_code=400, detail=f"Python Syntax Error in uploaded file at line {e.lineno}: {e.msg}")

    # Build standard object
    return UnifiedInput(
        raw_content=content_str,
        mode=InputMode.file_upload,
        language=language,
        extracted_functions=extracted_functions,
        warnings=warnings
    )
