from __future__ import annotations

from functools import lru_cache

from backend.agents.chains import TestGenerationChain
from backend.agents.llm_gateway import LLMGateway
from backend.agents.orchestrator import GenerationOrchestrator
from backend.core.cache import TTLCache
from backend.core.config import get_settings
from backend.core.database import DatabaseClient
from backend.util.logger import get_logger
from backend.input.handlers import InputProcessingService
from backend.input.intent_classifier import PromptIntentClassifier
from backend.input.js_parser import JavaScriptTypeScriptParser
from backend.input.parsers import ParserService
from backend.repositories.generation_repository import GenerationRepository
from backend.services.file_output_service import FileOutputService

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_repository() -> GenerationRepository:
    settings = get_settings()
    db = DatabaseClient(settings.database_url)
    return GenerationRepository(db)


@lru_cache(maxsize=1)
def get_orchestrator() -> GenerationOrchestrator:
    from backend.core.config import Settings

    settings: Settings = get_settings()
    llm = LLMGateway(settings)

    parser_cache = TTLCache[str, list](settings.parser_cache_ttl_seconds)
    intent_cache = TTLCache[str, object](settings.intent_cache_ttl_seconds)
    idempotency_cache = TTLCache[str, object](settings.idempotency_ttl_seconds)

    parser_service = ParserService(ttl_seconds=settings.parser_cache_ttl_seconds, cache=parser_cache)
    js_ts_parser = JavaScriptTypeScriptParser()
    intent_classifier = PromptIntentClassifier(llm, ttl_seconds=settings.intent_cache_ttl_seconds, cache=intent_cache)
    input_service = InputProcessingService(parser_service, js_ts_parser, intent_classifier)
    chain = TestGenerationChain(llm, settings)
    repository = get_repository()
    file_output_service = FileOutputService(
        repository_root=".",
        generated_tests_dir="generated_tests",
    )

    return GenerationOrchestrator(
        repository=repository,
        input_service=input_service,
        chain=chain,
        file_output_service=file_output_service,
        idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
        idempotency_cache=idempotency_cache,
    )
