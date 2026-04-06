from __future__ import annotations

import re

from backend.util.logger import get_logger
from backend.schemas import FunctionMetadata, Language, ParameterMetadata

logger = get_logger(__name__)

# ── regex patterns for JS/TS function extraction ──────────────────────

# function name(params)  /  async function name(params)  /  export [default] [async] function name
_FUNC_DECL_RE = re.compile(
	r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s+"
	r"(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)"
	r"\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)",
	re.MULTILINE,
)

# const/let/var name = (params) =>  /  const name = async (params) =>
_ARROW_RE = re.compile(
	r"(?:const|let|var)\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)"
	r"\s*=\s*(?:async\s+)?\((?P<params>[^)]*)\)\s*(?::\s*[^=]+?)?\s*=>",
	re.MULTILINE,
)

# const/let/var name = function(params)
_FUNC_EXPR_RE = re.compile(
	r"(?:const|let|var)\s+(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)"
	r"\s*=\s*(?:async\s+)?function\s*\((?P<params>[^)]*)\)",
	re.MULTILINE,
)

# Class method:  methodName(params)  /  async methodName(params)  /  static async methodName(params)
_METHOD_RE = re.compile(
	r"^\s+(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?"
	r"(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)"
	r"\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)",
	re.MULTILINE,
)

# import ... from 'module'  /  require('module')
_IMPORT_FROM_RE = re.compile(r"""(?:from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""")
_IMPORT_ALIAS_RE = re.compile(
	r"^\s*import\s+(?:\*\s+as\s+)?(?P<alias>[a-zA-Z_$][a-zA-Z0-9_$]*)\s+from\s+['\"](?P<module>[^'\"]+)['\"]",
	re.MULTILINE,
)
_DESTRUCTURED_IMPORT_RE = re.compile(
	r"^\s*import\s*\{(?P<names>[^}]+)\}\s*from\s+['\"](?P<module>[^'\"]+)['\"]",
	re.MULTILINE,
)
_REQUIRE_ALIAS_RE = re.compile(
	r"^\s*(?:const|let|var)\s+(?P<alias>[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*require\(\s*['\"](?P<module>[^'\"]+)['\"]\s*\)",
	re.MULTILINE,
)

_BUILTIN_SKIP = frozenset({"if", "else", "for", "while", "switch", "catch", "return", "throw", "new", "delete", "typeof", "void", "constructor"})


class JavaScriptTypeScriptParser:
	"""Local regex-based JS/TS function extractor — no LLM dependency."""

	def parse(self, language: Language, code: str) -> list[FunctionMetadata]:
		try:
			return self._extract(code)
		except Exception:
			logger.warning("js_ts_local_parser_failed", extra={"step": "parser", "status": "fallback"})
			return []

	# ──────────────────────────────────────────────────────────────────

	def _extract(self, code: str) -> list[FunctionMetadata]:
		seen: set[str] = set()
		results: list[FunctionMetadata] = []
		module_aliases = self._extract_import_aliases(code)

		for pattern in (_FUNC_DECL_RE, _ARROW_RE, _FUNC_EXPR_RE, _METHOD_RE):
			for match in pattern.finditer(code):
				name = match.group("name")
				if name in seen or name in _BUILTIN_SKIP:
					continue
				seen.add(name)
				raw_params = match.group("params").strip()
				params = self._parse_params(raw_params) if raw_params else []
				block_text = self._extract_function_block(code, match.start())
				dep_hints = self._extract_dependency_hints_for_block(block_text, module_aliases)
				results.append(
					FunctionMetadata(
						name=name,
						params=params,
						dependency_hints=dep_hints,
						decorators=[],
						docstring=None,
						return_annotation=None,
					)
				)

		logger.info("js_ts_parser_completed", extra={"step": "parser", "status": "ok", "function_count": len(results)})
		return results

	@staticmethod
	def _parse_params(raw: str) -> list[ParameterMetadata]:
		params: list[ParameterMetadata] = []
		for part in raw.split(","):
			part = part.strip()
			if not part:
				continue
			# Strip destructuring braces/brackets and defaults
			part = re.sub(r"\s*=\s*.*$", "", part)
			part = part.strip("{ }")
			# Strip type annotations  (name: Type)
			name_part = part.split(":")[0].strip().lstrip(".")
			# Handle rest params
			name_part = name_part.lstrip(".")
			if name_part and re.match(r"^[a-zA-Z_$]", name_part):
				params.append(ParameterMetadata(name=name_part, type_annotation=None))
		return params

	@staticmethod
	def _extract_import_aliases(code: str) -> dict[str, str]:
		aliases: dict[str, str] = {}
		for match in _IMPORT_ALIAS_RE.finditer(code):
			module = (match.group("module") or "").strip()
			alias = (match.group("alias") or "").strip()
			if module and alias and not module.startswith("."):
				aliases[alias] = module

		for match in _DESTRUCTURED_IMPORT_RE.finditer(code):
			module = (match.group("module") or "").strip()
			names = (match.group("names") or "").split(",")
			if not module or module.startswith("."):
				continue
			for name in names:
				cleaned = name.strip().split(" as ")[-1].strip()
				if cleaned:
					aliases[cleaned] = module

		for match in _REQUIRE_ALIAS_RE.finditer(code):
			module = (match.group("module") or "").strip()
			alias = (match.group("alias") or "").strip()
			if module and alias and not module.startswith("."):
				aliases[alias] = module

		return aliases

	@staticmethod
	def _extract_function_block(code: str, start_idx: int) -> str:
		line_start = code.rfind("\n", 0, start_idx)
		line_start = 0 if line_start == -1 else line_start + 1
		next_marker = code.find("\nfunction ", line_start + 1)
		for marker in ("\nconst ", "\nlet ", "\nvar ", "\nclass "):
			candidate = code.find(marker, line_start + 1)
			if candidate != -1 and (next_marker == -1 or candidate < next_marker):
				next_marker = candidate
		if next_marker == -1:
			return code[line_start:]
		return code[line_start:next_marker]

	@staticmethod
	def _extract_dependency_hints_for_block(block_text: str, module_aliases: dict[str, str]) -> list[str]:
		hints: set[str] = set()

		for alias, module in module_aliases.items():
			if re.search(rf"\b{re.escape(alias)}\b", block_text):
				hints.add(module)

		for m in _IMPORT_FROM_RE.finditer(block_text):
			module = m.group(1) or m.group(2)
			if module and not module.startswith("."):
				hints.add(module)

		return sorted(hints)
