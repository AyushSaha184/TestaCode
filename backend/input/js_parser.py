"""
backend/input/js_parser.py
---------------------------
LLM-based parser for JavaScript and TypeScript code.

Since Python's ast module can't parse JS/TS, we use a small, cheap LLM call
to extract function metadata into the same ExtractedFunction shape used by
the Python AST parser — so everything downstream is uniform.
"""

import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from src.utils.logger import get_logger
from backend.input.models import ExtractedFunction

logger = get_logger("ai_test_gen.js_parser")

# ─── Prompt Template ──────────────────────────────────────────────────────────

JS_TS_PARSER_PROMPT = PromptTemplate(
    template="""You are a senior JavaScript/TypeScript developer.
Analyze the following source code and extract metadata for every function,
method, and arrow-function assignment.

Source code:
---
{raw_code}
---

Return a JSON array of objects. Each object must have:
{{
  "name":             string  — function or variable name,
  "args":             list of strings  — parameter names,
  "type_annotations": object  — map of param name to type string (empty if no TS types),
  "docstring":        string or null  — JSDoc comment if present,
  "returns":          string or null  — return type if annotated,
  "decorators":       list of strings  — any decorators (empty for JS),
  "external_deps":    list of strings  — imported module names the function references
}}

Rules:
- Include named exports, default exports, class methods, and const arrow functions.
- Skip immediately-invoked function expressions (IIFEs).
- Output ONLY the raw JSON array — no markdown fences, no explanation.""",
    input_variables=["raw_code"],
)


def _get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` wrappers if the LLM adds them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
    return text


def parse_js_ts_code(code_str: str) -> Dict[str, Any]:
    """
    Sends JS/TS code to the LLM and returns the same dict shape as
    parse_python_code:  {"functions": [...], "warnings": [...]}.

    On LLM failure, returns an empty function list with a warning —
    this lets the pipeline continue using raw code context.
    """
    logger.info("js_ts_parsing_started", code_length=len(code_str))
    warnings: List[str] = []
    functions: List[ExtractedFunction] = []

    try:
        llm = _get_llm()
        chain = JS_TS_PARSER_PROMPT | llm
        result = chain.invoke({"raw_code": code_str})

        raw = _strip_markdown_json(result.content)
        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data).__name__}")

        for item in data:
            functions.append(
                ExtractedFunction(
                    name=item.get("name", "unknown"),
                    args=item.get("args", []),
                    type_annotations=item.get("type_annotations", {}),
                    docstring=item.get("docstring"),
                    returns=item.get("returns"),
                    decorators=item.get("decorators", []),
                    external_deps=item.get("external_deps", []),
                )
            )

        logger.info("js_ts_parsing_complete", functions_found=len(functions))

        if not functions:
            warnings.append("No functions detected in JS/TS code by LLM parser.")

        # Summarize external deps
        total_deps = sum(len(f.external_deps) for f in functions)
        if total_deps > 0:
            warnings.append(
                f"{total_deps} external import(s) detected across "
                f"{len(functions)} function(s) — mocking recommended."
            )

    except json.JSONDecodeError as e:
        logger.warning("js_ts_json_parse_failed", error=str(e))
        warnings.append("LLM-based JS/TS parser returned invalid JSON. Using raw code context.")
    except Exception as e:
        logger.error("js_ts_parsing_failed", error=str(e), exc_info=True)
        warnings.append(f"JS/TS parsing failed: {str(e)}. Using raw code context.")

    return {
        "functions": functions,
        "warnings": warnings,
    }
