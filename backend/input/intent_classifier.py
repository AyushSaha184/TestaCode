"""
backend/input/intent_classifier.py
-----------------------------------
Prompt Intent Classifier — a small, fast LLM call that extracts testing intent
from the user's free-text prompt BEFORE the main generation chain runs.

Keeping this as a separate module (not in chains.py) so it can be debugged
and tested independently from the generation pipeline.
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from src.utils.logger import get_logger
from backend.input.models import ClassifiedIntent

logger = get_logger("ai_test_gen.intent_classifier")

# ─── Prompt Template ──────────────────────────────────────────────────────────

INTENT_CLASSIFICATION_PROMPT = PromptTemplate(
    template="""You are a testing-requirement analyst. Analyze the following user 
instruction for test generation and extract structured intent.

User instruction:
---
"{user_prompt}"
---

Return a JSON object with exactly these keys:
{{
  "test_type":            one of ["unit", "integration", "edge_case", "mixed"],
  "target_scope":         one of ["all", "specific", "area"],
  "target_functions":     list of specific function names (empty list if scope is "all"),
  "target_framework":     one of ["pytest", "unittest", "jest", "mocha", "auto"],
  "special_requirements": list of any extra instructions (e.g. "include mocks", "add comments"),
  "confidence":           float 0-1 indicating how clear the instruction was
}}

Rules:
- If the user doesn't mention a specific test type, default to "unit".
- If no framework is mentioned, use "auto".
- If the user names specific functions, set target_scope to "specific" and list them.
- Output ONLY the raw JSON object — no markdown fences, no explanation.""",
    input_variables=["user_prompt"],
)


def _get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` wrappers if the LLM adds them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop first line (```json) and last line (```)
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
    return text


def classify_intent(user_prompt: str) -> ClassifiedIntent:
    """
    Runs a quick LLM call to classify the user's prompt into structured
    testing intent.  Returns a ClassifiedIntent with defaults if the call
    fails — never blocks the pipeline.
    """
    logger.info("intent_classification_started", prompt_length=len(user_prompt))

    try:
        llm = _get_llm()
        chain = INTENT_CLASSIFICATION_PROMPT | llm
        result = chain.invoke({"user_prompt": user_prompt})

        raw = _strip_markdown_json(result.content)
        data = json.loads(raw)

        intent = ClassifiedIntent(
            test_type=data.get("test_type", "unit"),
            target_scope=data.get("target_scope", "all"),
            target_functions=data.get("target_functions", []),
            target_framework=data.get("target_framework", "auto"),
            special_requirements=data.get("special_requirements", []),
            confidence=float(data.get("confidence", 0.5)),
        )

        logger.info(
            "intent_classified",
            test_type=intent.test_type,
            scope=intent.target_scope,
            framework=intent.target_framework,
            confidence=intent.confidence,
        )
        return intent

    except json.JSONDecodeError as e:
        logger.warning("intent_json_parse_failed", error=str(e))
    except Exception as e:
        logger.error("intent_classification_failed", error=str(e), exc_info=True)

    # Graceful fallback — never block the user
    return ClassifiedIntent()
