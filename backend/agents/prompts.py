from __future__ import annotations

import re

from backend.schemas import IntentClassification, UnifiedContext


PROMPT_TEMPLATE_REGISTRY: dict[str, str] = {
	"unit": (
		"Generate focused unit tests for target functions. "
		"Always include: happy-path, edge-case (empty, null/undefined, single-element, negative), "
		"error paths (exceptions, invalid inputs), and boundary conditions. "
		"Ensure all assertions are explicit. Only mock external imports that are NOT builtins or standard-library exceptions."
	),
	"edge": (
		"Generate edge-case oriented tests for invalid inputs, boundary conditions, and error paths. "
		"Always include: empty inputs, null/undefined/None, negative values, single-element inputs, "
		"type mismatches, maximum/minimum values, and strings with special characters. "
		"Prefer compact, high-signal assertions."
	),
	"integration": (
		"Generate integration-style tests validating component interactions, including dependency setup and data flow. "
		"Always include: normal flow, missing dependency, failure recovery, and boundary data scenarios."
	),
	"mixed": (
		"Generate a balanced test suite covering happy path, error path, and edge-case behavior. "
		"Always include: empty, null/undefined, single-element, negative, and boundary inputs. "
		"Only mock real external dependencies, not builtins or standard-library exceptions."
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


def _relevant_code_excerpt(context: UnifiedContext, max_lines: int = 200, window: int = 24) -> str:
	lines = context.raw_code.splitlines()
	if len(lines) <= max_lines:
		return context.raw_code

	decl_index: dict[str, int] = {}
	decl_pattern = re.compile(
		r"^\s*(?:(?:async\s+def|def)\s+(?P<py>[A-Za-z_][A-Za-z0-9_]*)\b|"
		r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(?P<jsf>[A-Za-z_$][A-Za-z0-9_$]*)\b|"
		r"(?:const|let|var)\s+(?P<jsv>[A-Za-z_$][A-Za-z0-9_$]*)\s*=|"
		r"(?:static\s+)?(?:async\s+)?(?P<method>[A-Za-z_$][A-Za-z0-9_$]*)\s*\()"
	)
	for idx, line in enumerate(lines):
		match = decl_pattern.search(line)
		if not match:
			continue
		name = match.group("py") or match.group("jsf") or match.group("jsv") or match.group("method")
		if name and name not in decl_index:
			decl_index[name] = idx

	snippet_indexes: set[int] = set()
	for fn in context.function_metadata:
		idx = decl_index.get(fn.name)
		if idx is not None:
			start = max(0, idx - 3)
			end = min(len(lines), idx + window)
			snippet_indexes.update(range(start, end))
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


def build_generation_prompts(context: UnifiedContext) -> tuple[str, str]:
	"""Single combined analysis+generation prompt. Replaces the old two-call approach."""
	mock_instructions = {
		"python": "Import the module under test directly. Only use patch/MagicMock when the code imports external modules or services that are not Python builtins or standard library exceptions.",
		"javascript": "Import the module under test with require/import. Only use jest.mock when the code imports external modules or services — never mock built-in functions or the module being tested itself.",
		"typescript": "Import the module under test. Only use jest.mock for real external service dependencies, not for internal utilities or built-ins.",
		"java": "Use JUnit-style tests with Mockito only for external collaborators (databases, HTTP clients, etc.). Do not mock java.lang types.",
		"rust": "Use cargo test conventions; prefer inline test modules and lightweight stubs. Do not mock standard library types.",
		"golang": "Use go test conventions; isolate real external dependencies with interfaces or small fakes. Do not mock standard library packages.",
		"csharp": "Use xUnit conventions with Moq-style substitutes only for external dependencies. Do not mock System types.",
	}
	mock_instruction = mock_instructions.get(context.detected_language.value, "Mock only real external dependencies — never builtins or standard library types.")
	generation_instruction = select_generation_instruction(context.classified_intent)

	language = context.detected_language.value
	import_instructions = _import_instructions(language)

	system_prompt = (
		"You are an expert test generator. "
		"Analyze the code behavior: valid paths, error paths, edge cases, and boundaries. "
		"Base test expectations on what the code actually does — never invent expected values you can't derive from the source. "
		"Use descriptive test names that explain the behavior being verified (e.g., 'returns_empty_string_for_null_input', not 'test1'). "
		"Produce production-ready test code only. "
		"Do NOT output analysis text, markdown fences, or explanations — only test code."
	)

	user_prompt = (
		f"{generation_instruction}\n"
		f"Language: {language}\n"
		f"Target scope/functions: {context.classified_intent.target_scope}\n"
		f"Framework: {context.classified_intent.target_framework.value}\n"
		f"Special requirements: {context.classified_intent.special_requirements}\n"
		f"{import_instructions}\n"
		f"Mocking instructions: {mock_instruction}\n"
		f"Function metadata:\n{_compact_function_summary(context)}\n"
		f"Code under test:\n{_relevant_code_excerpt(context)}\n"
		f"Return only test code. Do NOT wrap output in code fences."
	)
	return system_prompt, user_prompt


def _import_instructions(language: str) -> str:
	if language == "python":
		return "Always include an import statement for the module under test at the top of the generated test file (e.g., 'from module import func' or 'import module'). Use unittest or pytest."
	if language in ("javascript", "typescript"):
		return "Always include a require or import statement for the module under test at the top of the generated test file. Use Jest conventions with 'describe', 'test', and 'expect'."
	return "Always include the necessary import/require/import statements at the top of the generated test file."


def build_correction_prompts(language: str, code: str, error: str) -> tuple[str, str]:
	system_prompt = (
		"You are a syntax correction assistant. Return corrected code only. "
		"Preserve all existing imports and test coverage. Do NOT introduce new mocks unless the error requires it. "
		"Do NOT wrap output in code fences."
	)
	user_prompt = (
		f"Language: {language}\n"
		f"Fix the syntax error while preserving test intent, imports, and all test cases.\n"
		f"Syntax error:\n{error}\n"
		f"Code:\n{code}"
	)
	return system_prompt, user_prompt


def build_self_eval_prompts(context: UnifiedContext, generated_code: str) -> tuple[str, str]:
	system_prompt = (
		"Self-evaluate generated tests. Return strict JSON with keys quality_score (0..10) and uncovered_areas (list[str]). "
		"Do NOT include any other keys or explanation text."
	)
	user_prompt = (
		"Score criteria (0-2 each): happy path coverage, error path coverage, edge case coverage, "
		"mocking correctness, assertion quality.\n"
		"Deduct 2 points for each of these issues:\n"
		"- Missing imports/require statements for the module under test\n"
		"- Unnecessary mock blocks (jest.mock, @patch, etc.) that wrap the module being tested\n"
		"- Test expectations that contradict actual code behavior (e.g., expecting return value when the code would throw)\n"
		"- Tests that use the module under test without importing it first\n"
		f"Language: {context.detected_language.value}\n"
		f"Intent: {context.classified_intent.model_dump_json()}\n"
		f"Function metadata:\n{_compact_function_summary(context)}\n"
		f"Generated tests:\n{generated_code}"
	)
	return system_prompt, user_prompt
