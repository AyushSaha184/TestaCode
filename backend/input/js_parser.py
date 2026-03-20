from __future__ import annotations

from backend.agents.llm_gateway import LLMGateway
from backend.core.logger import get_logger
from backend.schemas import FunctionMetadata, Language, ParameterMetadata

logger = get_logger(__name__)


class JavaScriptTypeScriptParser:
	def __init__(self, llm: LLMGateway) -> None:
		self.llm = llm

	def parse(self, language: Language, code: str) -> list[FunctionMetadata]:
		system_prompt = (
			"You are a JavaScript/TypeScript parser. Return strict JSON only with schema: "
			"{\"functions\": [{\"name\": str, \"params\": [str], \"dependency_hints\": [str]}]}"
		)
		user_prompt = f"Language: {language.value}\nCode:\n{code}"

		response = self.llm.invoke_json(system_prompt, user_prompt, tier="fast")
		raw_items = response.get("functions", [])
		output: list[FunctionMetadata] = []

		for item in raw_items:
			params = [ParameterMetadata(name=str(param), type_annotation=None) for param in item.get("params", [])]
			output.append(
				FunctionMetadata(
					name=str(item.get("name", "unknown")),
					params=params,
					dependency_hints=[str(dep) for dep in item.get("dependency_hints", [])],
					decorators=[],
					docstring=None,
					return_annotation=None,
				)
			)

		logger.info("js_ts_parser_completed", extra={"step": "parser", "status": "ok"})
		return output
