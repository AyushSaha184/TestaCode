from __future__ import annotations

from backend.schemas import IntentClassification, UnifiedContext


PROMPT_TEMPLATE_REGISTRY: dict[str, str] = {
	"unit": (
		"Generate focused unit tests for target functions. "
		"Ensure assertions are explicit and dependencies are mocked."
	),
	"edge": (
		"Generate edge-case oriented tests for invalid inputs, boundary conditions, and error paths. "
		"Prefer compact, high-signal assertions."
	),
	"integration": (
		"Generate integration-style tests validating component interactions, including dependency setup and data flow."
	),
	"mixed": (
		"Generate a balanced test suite covering happy path, error path, and edge-case behavior with pragmatic mocking."
	),
}


def select_generation_instruction(intent: IntentClassification) -> str:
	return PROMPT_TEMPLATE_REGISTRY.get(intent.test_type.value, PROMPT_TEMPLATE_REGISTRY["mixed"])


def build_analysis_prompts(context: UnifiedContext) -> tuple[str, str]:
	system_prompt = (
		"You are a senior test architect. Produce behavior-oriented analysis before writing tests."
	)
	user_prompt = (
		"Analyze code under test and return concise markdown with sections:\n"
		"1) Expected valid behavior\n"
		"2) Invalid input behavior\n"
		"3) Dependency and mock strategy\n"
		"4) High-priority scenarios\n"
		f"Language: {context.detected_language.value}\n"
		f"Prompt intent: {context.classified_intent.model_dump_json()}\n"
		f"Function metadata: {[fn.model_dump() for fn in context.function_metadata]}\n"
		f"Code:\n{context.raw_code}"
	)
	return system_prompt, user_prompt


def build_generation_prompts(context: UnifiedContext, analysis_text: str) -> tuple[str, str]:
	system_prompt = "You are an expert test generator producing production-ready test code only."

	mock_instruction = (
		"Use patch and MagicMock for Python dependency mocking when needed."
		if context.detected_language.value == "python"
		else "Use jest.mock for JavaScript/TypeScript dependency mocking when needed."
	)
	generation_instruction = select_generation_instruction(context.classified_intent)

	user_prompt = (
		f"{generation_instruction}\n"
		f"Language: {context.detected_language.value}\n"
		f"Target scope/functions: {context.classified_intent.target_scope}\n"
		f"Framework: {context.classified_intent.target_framework.value}\n"
		f"Special requirements: {context.classified_intent.special_requirements}\n"
		f"Mocking instructions: {mock_instruction}\n"
		f"Analysis:\n{analysis_text}\n"
		f"Code under test:\n{context.raw_code}\n"
		"Return only test code."
	)
	return system_prompt, user_prompt


def build_correction_prompts(language: str, code: str, error: str) -> tuple[str, str]:
	system_prompt = "You are a syntax correction assistant. Return corrected code only."
	user_prompt = (
		f"Language: {language}\n"
		f"Fix syntax error while preserving test intent.\n"
		f"Syntax error:\n{error}\n"
		f"Code:\n{code}"
	)
	return system_prompt, user_prompt


def build_self_eval_prompts(context: UnifiedContext, generated_code: str) -> tuple[str, str]:
	system_prompt = (
		"Self-evaluate generated tests. Return strict JSON with keys quality_score (0..10) and uncovered_areas (list[str])."
	)
	user_prompt = (
		"Score criteria (0-2 each): happy path coverage, error path coverage, edge case coverage, "
		"mocking correctness, assertion quality.\n"
		f"Language: {context.detected_language.value}\n"
		f"Intent: {context.classified_intent.model_dump_json()}\n"
		f"Code under test:\n{context.raw_code}\n"
		f"Generated tests:\n{generated_code}"
	)
	return system_prompt, user_prompt
