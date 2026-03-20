from __future__ import annotations

from backend.core.exceptions import AppError
from backend.core.logger import get_logger
from backend.input.intent_classifier import PromptIntentClassifier
from backend.input.js_parser import JavaScriptTypeScriptParser
from backend.input.parsers import ParserService
from backend.schemas import FunctionMetadata, GenerationRequest, Language, UnifiedContext

logger = get_logger(__name__)


class InputProcessingService:
	def __init__(
		self,
		parser_service: ParserService,
		js_ts_parser: JavaScriptTypeScriptParser,
		intent_classifier: PromptIntentClassifier,
	) -> None:
		self.parser_service = parser_service
		self.js_ts_parser = js_ts_parser
		self.intent_classifier = intent_classifier

	def _parse_functions(self, session_id: str, language: Language, code: str) -> list[FunctionMetadata]:
		cached = self.parser_service.get_cached(session_id, language, code)
		if cached is not None:
			logger.info("parser_cache_hit", extra={"step": "parser", "status": "ok"})
			return cached

		if language == Language.python:
			parsed = self.parser_service.python_parser.parse(code)
		elif language in (Language.javascript, Language.typescript):
			parsed = self.js_ts_parser.parse(language, code)
		elif language == Language.java:
			parsed = []
		else:
			raise AppError(f"Unsupported language '{language.value}'", status_code=422)

		self.parser_service.set_cached(session_id, language, code, parsed)
		return parsed

	def build_unified_context(self, request: GenerationRequest, base_warnings: list[str]) -> UnifiedContext:
		logger.info("input_processing_started", extra={"step": "input", "status": "processing"})
		function_metadata = self._parse_functions(request.session_id, request.language, request.code_content)
		intent, intent_warnings = self.intent_classifier.classify_for_session(
			session_id=request.session_id,
			prompt=request.user_prompt,
			language=request.language,
			code=request.code_content,
		)

		warnings = [*base_warnings, *intent_warnings]
		context = UnifiedContext(
			raw_code=request.code_content,
			detected_language=request.language,
			function_metadata=function_metadata,
			classified_intent=intent,
			original_prompt=request.user_prompt,
			warnings=warnings,
		)
		logger.info("input_processing_completed", extra={"step": "input", "status": "ok"})
		return context
