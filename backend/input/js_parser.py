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
		dep_hints = self._extract_dependency_hints(code)

		for pattern in (_FUNC_DECL_RE, _ARROW_RE, _FUNC_EXPR_RE, _METHOD_RE):
			for match in pattern.finditer(code):
				name = match.group("name")
				if name in seen or name in _BUILTIN_SKIP:
					continue
				seen.add(name)
				raw_params = match.group("params").strip()
				params = self._parse_params(raw_params) if raw_params else []
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
	def _extract_dependency_hints(code: str) -> list[str]:
		hints: set[str] = set()
		for m in _IMPORT_FROM_RE.finditer(code):
			module = m.group(1) or m.group(2)
			if module and not module.startswith("."):
				hints.add(module)
		return sorted(hints)
