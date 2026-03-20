from __future__ import annotations

from functools import lru_cache

from backend.agents.chains import TestGenerationChain
from backend.agents.llm_gateway import LLMGateway
from backend.agents.orchestrator import GenerationOrchestrator
from backend.core.cache import RedisTTLCache, TTLCache
from backend.core.config import Settings, get_settings
from backend.core.database import DatabaseClient
from backend.core.logger import get_logger
from backend.input.handlers import InputProcessingService
from backend.input.intent_classifier import PromptIntentClassifier
from backend.input.js_parser import JavaScriptTypeScriptParser
from backend.input.parsers import ParserService
from backend.repositories.generation_repository import GenerationRepository
from backend.services.file_output_service import FileOutputService
from backend.services.git_integration_service import GitIntegrationService
from backend.services.supabase_storage_service import SupabaseStorageService

logger = get_logger(__name__)


def _create_redis_client(settings: Settings):
    from redis import Redis

    if settings.redis_url:
        return Redis.from_url(settings.redis_url, decode_responses=False)

    if settings.redis_host:
        kwargs = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "decode_responses": False,
            "ssl": settings.redis_ssl,
        }
        if settings.redis_username:
            kwargs["username"] = settings.redis_username
        if settings.redis_password:
            kwargs["password"] = settings.redis_password
        return Redis(**kwargs)

    return None


@lru_cache(maxsize=1)
def get_repository() -> GenerationRepository:
    settings = get_settings()
    db = DatabaseClient(settings.database_url)
    return GenerationRepository(db)


@lru_cache(maxsize=1)
def get_storage_service() -> SupabaseStorageService | None:
    settings = get_settings()
    if not settings.has_supabase_storage():
        return None
    return SupabaseStorageService(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
        bucket=settings.supabase_storage_bucket,
        public_bucket=settings.supabase_storage_public,
        signed_url_ttl_seconds=settings.supabase_signed_url_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_orchestrator() -> GenerationOrchestrator:
    settings: Settings = get_settings()
    llm = LLMGateway(settings)

    parser_cache = TTLCache[str, list](settings.parser_cache_ttl_seconds)
    intent_cache = TTLCache[str, object](settings.intent_cache_ttl_seconds)
    idempotency_cache = TTLCache[str, object](settings.idempotency_ttl_seconds)

    if settings.use_redis_cache:
        try:
            redis_client = _create_redis_client(settings)
            if redis_client is None:
                logger.warning(
                    "redis_cache_unconfigured_fallback",
                    extra={"step": "cache", "status": "fallback"},
                )
            else:
                redis_client.ping()
                parser_cache = RedisTTLCache(redis_client, settings.parser_cache_ttl_seconds, f"{settings.redis_key_prefix}:parser")
                intent_cache = RedisTTLCache(redis_client, settings.intent_cache_ttl_seconds, f"{settings.redis_key_prefix}:intent")
                idempotency_cache = RedisTTLCache(redis_client, settings.idempotency_ttl_seconds, f"{settings.redis_key_prefix}:idempotency")
                logger.info("redis_cache_enabled", extra={"step": "cache", "status": "ok"})
        except Exception:
            logger.exception("redis_cache_init_failed", extra={"step": "cache", "status": "fallback"})

    parser_service = ParserService(ttl_seconds=settings.parser_cache_ttl_seconds, cache=parser_cache)
    js_ts_parser = JavaScriptTypeScriptParser(llm)
    intent_classifier = PromptIntentClassifier(llm, ttl_seconds=settings.intent_cache_ttl_seconds, cache=intent_cache)
    input_service = InputProcessingService(parser_service, js_ts_parser, intent_classifier)
    chain = TestGenerationChain(llm)
    repository = get_repository()
    storage_service = get_storage_service()
    file_output_service = FileOutputService(
        repository_root=settings.resolved_repository_root(),
        generated_tests_dir=settings.generated_tests_dir,
        storage_service=storage_service,
    )
    git_integration_service = GitIntegrationService(
        repository_root=settings.resolved_repository_root(),
        generated_tests_dir=settings.generated_tests_dir,
        author_name=settings.git_author_name,
        author_email=settings.git_author_email,
        enable_git_push=settings.enable_git_push,
    )

    return GenerationOrchestrator(
        repository=repository,
        input_service=input_service,
        chain=chain,
        file_output_service=file_output_service,
        git_integration_service=git_integration_service,
        idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
        idempotency_cache=idempotency_cache,
    )
