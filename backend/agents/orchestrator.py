import json
from backend.core.config import logger
from backend.input.models import UnifiedContext
from backend.agents.chains import (
    run_code_analysis,
    run_test_generation,
)
from backend.agents.tools import check_syntax


def sanitize_and_fix_code(agent_output: str, language: str, retries_left: int = 2) -> dict:
    """
    Validates syntax. If broken, loops back up to 2 times for LLM self-correction.
    Returns dict with 'success', 'code', and optionally 'error' and 'iterations'.
    """
    iterations = []
    is_valid, error_msg = check_syntax(agent_output, language)

    if is_valid:
        return {"success": True, "code": agent_output, "iterations": iterations}

    if retries_left <= 0:
        logger.error(f"Auto-correction failed after max retries. Syntax Error: {error_msg}")
        iterations.append({"attempt": "final", "error": error_msg, "fixed": False})
        return {"success": False, "code": agent_output, "error": error_msg, "iterations": iterations}

    logger.warning(f"Syntax Error caught. Sending to LLM Self-Correction. {retries_left} retries left.")
    iterations.append({"attempt": 3 - retries_left, "error": error_msg, "fixed": False})

    from backend.agents.chains import get_llm
    from langchain.prompts import PromptTemplate

    fix_prompt = PromptTemplate(
        template="""You are an expert developer. The following code failed syntax validation:
```
{code}
```
Error: {error}

Please output ONLY the corrected code without markdown ticks. Maintain all intended testing logic.""",
        input_variables=["code", "error"],
    )

    llm = get_llm()
    chain = fix_prompt | llm
    fixed_response = chain.invoke({"code": agent_output, "error": error_msg})

    # Recurse
    result = sanitize_and_fix_code(fixed_response.content, language, retries_left - 1)
    result["iterations"] = iterations + result.get("iterations", [])
    return result


def process_generation_flow(unified_context: UnifiedContext) -> dict:
    """
    Main orchestrator tying the input processing layer to the LangChain generation pipeline.

    Flow:
      1. Run code analysis (Stage 1)
      2. Run test generation (Stage 2)
      3. Validate & auto-correct (Stage 3)
      4. Return result with code, warnings, and metadata

    Full self-evaluation (quality scoring) will be added in Phase 3.
    """
    language = unified_context.language.value
    intent = unified_context.classified_intent

    # Determine framework
    if intent.target_framework and intent.target_framework != "auto":
        framework = intent.target_framework
    elif language == "python":
        framework = "pytest"
    elif language in ("javascript", "typescript"):
        framework = "jest"
    else:
        framework = "pytest"

    # ─── Stage 1: Code Analysis ───────────────────────────────────────────────
    logger.info("Executing Agent Stage 1: Code Analysis")
    analysis = run_code_analysis(unified_context.raw_code, language)

    # ─── Stage 2: Test Generation ─────────────────────────────────────────────
    logger.info("Executing Agent Stage 2: Test Code Generation")
    code_context = f"\nOriginal Code Context:\n{unified_context.raw_code}\n"

    raw_tests = run_test_generation(
        analysis=analysis,
        code_context=code_context,
        language=language,
        framework=framework,
        mock=True,
        edge=(intent.test_type in ("edge_case", "mixed")),
    )

    # ─── Stage 3: Validation & Auto-Correction ───────────────────────────────
    logger.info("Executing Agent Stage 3: Syntax Validation & Auto-Correction")
    validation_result = sanitize_and_fix_code(raw_tests, language)

    # Build warnings list
    all_warnings = list(unified_context.warnings)
    if not validation_result["success"]:
        all_warnings.append(
            f"Syntax validation failed after retries: {validation_result.get('error', 'Unknown')}"
        )

    # Serialize intent for DB storage
    intent_json = json.dumps(intent.model_dump())

    return {
        "status": "success" if validation_result["success"] else "failed",
        "code": validation_result["code"],
        "warnings": all_warnings,
        "quality_score": None,  # Phase 3: self-evaluation
        "uncovered_areas": [],  # Phase 3: self-evaluation
        "framework_used": framework,
        "classified_intent": intent_json,
        "analysis": analysis,
        "iterations": validation_result.get("iterations", []),
    }
