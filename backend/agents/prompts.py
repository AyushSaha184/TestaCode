from __future__ import annotations

import re

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


def _compact_function_summary(context: UnifiedContext) -> str:
	"""Build a compact text summary of function metadata (avoids sending full source)."""
	if not context.function_metadata:
		return "No function metadata extracted."
	lines: list[str] = []
	for fn in context.function_metadata:
		params = ", ".join(p.name for p in fn.params)
		ret = f" -> {fn.return_annotation}" if fn.return_annotation else ""
		doc = f'  """{fn.docstring}"""' if fn.docstring else ""
		deps = f"  deps: {', '.join(fn.dependency_hints)}" if fn.dependency_hints else ""
		lines.append(f"- {fn.name}({params}){ret}{doc}{deps}")
	return "\n".join(lines)


def _truncated_code(code: str, max_lines: int = 200) -> str:
	"""Return code truncated to max_lines with a marker if cut."""
	lines = code.splitlines()
	if len(lines) <= max_lines:
		return code
	return "\n".join(lines[:max_lines]) + f"\n# ... ({len(lines) - max_lines} lines truncated)"


def _relevant_code_excerpt(context: UnifiedContext, max_lines: int = 200, window: int = 24) -> str:
	lines = context.raw_code.splitlines()
	if len(lines) <= max_lines:
		return context.raw_code

	snippet_indexes: set[int] = set()
	for fn in context.function_metadata:
		name = re.escape(fn.name)
		patterns = (
			rf"^\s*(?:async\s+def|def)\s+{name}\b",
			rf"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+{name}\b",
			rf"^\s*(?:const|let|var)\s+{name}\s*=",
			rf"^\s*(?:static\s+)?(?:async\s+)?{name}\s*\(",
		)
		for idx, line in enumerate(lines):
			if any(re.search(pattern, line) for pattern in patterns):
				start = max(0, idx - 3)
				end = min(len(lines), idx + window)
				snippet_indexes.update(range(start, end))
				break
		if len(snippet_indexes) >= max_lines:
			break

	if not snippet_indexes:
		head = lines[: max_lines // 2]
		tail = lines[-(max_lines - len(head)) :]
		return "\n".join(head + ["# ... relevant code omitted ..."] + tail)

	selected = [lines[idx] for idx in sorted(snippet_indexes)[:max_lines]]
	omitted = max(0, len(lines) - len(selected))
	if omitted:
		selected.append(f"# ... ({omitted} additional lines omitted)")
	return "\n".join(selected)


def build_analysis_summary(context: UnifiedContext) -> str:
	targets = ", ".join(fn.name for fn in context.function_metadata[:6]) or "all extracted behavior"
	deps = sorted({hint for fn in context.function_metadata for hint in fn.dependency_hints})
	deps_text = ", ".join(deps[:8]) if deps else "none detected"
	return (
		f"Intent: {context.classified_intent.test_type.value} tests for {targets}.\n"
		f"Framework: {context.classified_intent.target_framework.value}.\n"
		f"Dependency hints: {deps_text}."
	)


# ── Keep for backward compat; no longer called on critical path ──

def build_analysis_prompts(context: UnifiedContext) -> tuple[str, str]:
	"""Deprecated: analysis is now inlined into the generation prompt."""
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
		f"Function metadata:\n{_compact_function_summary(context)}\n"
		f"Code:\n{_relevant_code_excerpt(context)}"
	)
	return system_prompt, user_prompt


def build_generation_prompts(context: UnifiedContext) -> tuple[str, str]:
	"""Single combined analysis+generation prompt. Replaces the old two-call approach."""
	mock_instruction = (
		"Use patch and MagicMock for Python dependency mocking when needed."
		if context.detected_language.value == "python"
		else "Use jest.mock for JavaScript/TypeScript dependency mocking when needed."
	)
	generation_instruction = select_generation_instruction(context.classified_intent)

	system_prompt = (
		"You are an expert test generator. "
		"First, briefly analyze the code to identify: valid behavior, error paths, dependency/mock strategy, and high-priority scenarios. "
		"Then produce production-ready test code only. Do not output analysis text — only test code."
	)

	user_prompt = (
		f"{generation_instruction}\n"
		f"Language: {context.detected_language.value}\n"
		f"Target scope/functions: {context.classified_intent.target_scope}\n"
		f"Framework: {context.classified_intent.target_framework.value}\n"
		f"Special requirements: {context.classified_intent.special_requirements}\n"
		f"Mocking instructions: {mock_instruction}\n"
		f"Function metadata:\n{_compact_function_summary(context)}\n"
		f"Code under test:\n{_relevant_code_excerpt(context)}\n"
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
		f"Function metadata:\n{_compact_function_summary(context)}\n"
		f"Generated tests:\n{generated_code}"
	)
	return system_prompt, user_prompt
