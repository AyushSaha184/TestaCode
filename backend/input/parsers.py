from __future__ import annotations

import ast
import hashlib
from typing import Iterable

from backend.core.cache import CacheBackend, TTLCache
from backend.core.logger import get_logger
from backend.schemas import FunctionMetadata, Language, ParameterMetadata

logger = get_logger(__name__)


class PythonFunctionParser:
	def parse(self, code: str) -> list[FunctionMetadata]:
		tree = ast.parse(code)
		functions: list[FunctionMetadata] = []

		for node in ast.walk(tree):
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				continue

			params = [
				ParameterMetadata(
					name=arg.arg,
					type_annotation=ast.unparse(arg.annotation) if arg.annotation else None,
				)
				for arg in node.args.args
			]

			dependency_hints = sorted(_find_dependency_candidates(node, params))
			decorators = [ast.unparse(deco) for deco in node.decorator_list]
			functions.append(
				FunctionMetadata(
					name=node.name,
					params=params,
					return_annotation=ast.unparse(node.returns) if node.returns else None,
					docstring=ast.get_docstring(node),
					decorators=decorators,
					dependency_hints=dependency_hints,
				)
			)

		logger.info("python_parser_completed", extra={"step": "parser", "status": "ok"})
		return functions


def _find_dependency_candidates(node: ast.AST, params: Iterable[ParameterMetadata]) -> set[str]:
	param_names = {item.name for item in params}
	local_names: set[str] = set(param_names)
	dependency_names: set[str] = set()

	for child in ast.walk(node):
		if isinstance(child, ast.Assign):
			for target in child.targets:
				if isinstance(target, ast.Name):
					local_names.add(target.id)
		if isinstance(child, ast.For) and isinstance(child.target, ast.Name):
			local_names.add(child.target.id)
		if isinstance(child, ast.With):
			for item in child.items:
				if item.optional_vars and isinstance(item.optional_vars, ast.Name):
					local_names.add(item.optional_vars.id)
		if isinstance(child, ast.Call):
			name = _call_name(child.func)
			if name and name.split(".")[0] not in local_names:
				dependency_names.add(name)

	return dependency_names


def _call_name(func: ast.AST) -> str | None:
	if isinstance(func, ast.Name):
		return func.id
	if isinstance(func, ast.Attribute):
		base = _call_name(func.value)
		if base:
			return f"{base}.{func.attr}"
		return func.attr
	return None


class ParserService:
	def __init__(self, ttl_seconds: int, cache: CacheBackend[str, list[FunctionMetadata]] | None = None) -> None:
		self.cache = cache or TTLCache[str, list[FunctionMetadata]](ttl_seconds)
		self.python_parser = PythonFunctionParser()

	def _cache_key(self, session_id: str, language: Language, code: str) -> str:
		digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
		return f"{session_id}:{language.value}:{digest}"

	def get_cached(self, session_id: str, language: Language, code: str) -> list[FunctionMetadata] | None:
		return self.cache.get(self._cache_key(session_id, language, code))

	def set_cached(self, session_id: str, language: Language, code: str, value: list[FunctionMetadata]) -> None:
		self.cache.set(self._cache_key(session_id, language, code), value)
