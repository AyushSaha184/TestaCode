from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()


class Settings(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	app_name: str = Field(default=os.getenv("APP_NAME", "AI Test Generation Backend"))
	app_env: str = Field(default=os.getenv("APP_ENV", "development"))
	log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
	log_file: str = Field(default=os.getenv("LOG_FILE", "logs/backend.log"))
	log_to_file: bool = Field(default=os.getenv("LOG_TO_FILE", "true").lower() == "true")
	allowed_origins: List[str] = Field(
		default_factory=lambda: [
			origin.strip()
			for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
			if origin.strip()
		]
	)
	database_url: str = Field(
		default=os.getenv("DATABASE_URL")
		or os.getenv("RENDER_POSTGRES_URL")
		or os.getenv("SUPABASE_DB_URL", "")
	)
	supabase_url: str = Field(default=os.getenv("SUPABASE_URL", ""))
	supabase_anon_key: str = Field(default=os.getenv("SUPABASE_ANON_KEY", ""))
	supabase_service_role_key: str = Field(default=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
	supabase_storage_bucket: str = Field(default=os.getenv("SUPABASE_STORAGE_BUCKET", "code-files"))
	supabase_storage_public: bool = Field(default=os.getenv("SUPABASE_STORAGE_PUBLIC", "false").lower() == "true")
	supabase_signed_url_ttl_seconds: int = Field(default=int(os.getenv("SUPABASE_SIGNED_URL_TTL_SECONDS", "3600")))
	render_external_url: str = Field(default=os.getenv("RENDER_EXTERNAL_URL", ""))
	vercel_frontend_url: str = Field(default=os.getenv("VERCEL_FRONTEND_URL", ""))

	max_upload_kb: int = Field(default=int(os.getenv("MAX_UPLOAD_KB", "50")))
	request_timeout_seconds: int = Field(default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "40")))

	parser_cache_ttl_seconds: int = Field(default=int(os.getenv("PARSER_CACHE_TTL_SECONDS", "600")))
	intent_cache_ttl_seconds: int = Field(default=int(os.getenv("INTENT_CACHE_TTL_SECONDS", "600")))
	idempotency_ttl_seconds: int = Field(default=int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "3600")))
	use_redis_cache: bool = Field(default=os.getenv("USE_REDIS_CACHE", "true").lower() == "true")
	redis_url: str = Field(default=os.getenv("REDIS_URL", ""))
	redis_host: str = Field(default=os.getenv("REDIS_HOST", ""))
	redis_port: int = Field(default=int(os.getenv("REDIS_PORT", "6379")))
	redis_username: str = Field(default=os.getenv("REDIS_USERNAME", ""))
	redis_password: str = Field(default=os.getenv("REDIS_PASSWORD", ""))
	redis_ssl: bool = Field(default=os.getenv("REDIS_SSL", "true").lower() == "true")
	redis_key_prefix: str = Field(default=os.getenv("REDIS_KEY_PREFIX", "testacode"))

	llm_enabled: bool = Field(default=os.getenv("LLM_ENABLED", "false").lower() == "true")
	llm_api_key: str = Field(default=os.getenv("LLM_API_KEY", ""))
	cerebras_api_key: str = Field(default=os.getenv("CEREBRAS_API_KEY", ""))
	openrouter_api_key: str = Field(default=os.getenv("OPENROUTER_API_KEY", ""))
	google_api_key: str = Field(default=os.getenv("GOOGLE_API_KEY", ""))
	llm_base_url: str = Field(default=os.getenv("LLM_BASE_URL", ""))
	llm_fast_model: str = Field(default=os.getenv("LLM_FAST_MODEL", "gpt-4o-mini"))
	llm_strong_model: str = Field(default=os.getenv("LLM_STRONG_MODEL", "qwen-3-235b-2507"))
	llm_timeout_seconds: int = Field(default=int(os.getenv("LLM_TIMEOUT_SECONDS", "25")))
	llm_max_retries: int = Field(default=int(os.getenv("LLM_MAX_RETRIES", "3")))
	llm_enable_self_eval: bool = Field(default=os.getenv("LLM_ENABLE_SELF_EVAL", "false").lower() == "true")
	llm_gen_timeout_seconds: int = Field(default=int(os.getenv("LLM_GEN_TIMEOUT_SECONDS", "20")))
	llm_gen_max_retries: int = Field(default=int(os.getenv("LLM_GEN_MAX_RETRIES", "1")))

	auto_commit_default: bool = Field(default=os.getenv("AUTO_COMMIT_DEFAULT", "false").lower() == "true")
	git_author_name: str = Field(default=os.getenv("GIT_AUTHOR_NAME", "ai-test-gen-bot"))
	git_author_email: str = Field(default=os.getenv("GIT_AUTHOR_EMAIL", "ai-test-gen-bot@example.com"))
	enable_git_push: bool = Field(default=os.getenv("ENABLE_GIT_PUSH", "false").lower() == "true")
	repository_root: str = Field(default=os.getenv("REPOSITORY_ROOT", "."))
	generated_tests_dir: str = Field(default=os.getenv("GENERATED_TESTS_DIR", "generated_tests"))

	def resolved_repository_root(self) -> str:
		return str(Path(self.repository_root).resolve())

	def validate_production_configuration(self) -> None:
		if self.app_env.lower() != "production":
			return
		if not self.database_url:
			raise ValueError("DATABASE_URL is required in production")
		if self.supabase_service_role_key and not self.supabase_url:
			raise ValueError("SUPABASE_URL is required when SUPABASE_SERVICE_ROLE_KEY is set")
		if self.vercel_frontend_url and self.vercel_frontend_url not in self.cors_origins():
			raise ValueError("VERCEL_FRONTEND_URL must be included in CORS origins")

	def cors_origins(self) -> list[str]:
		origins = set(self.allowed_origins)
		if self.vercel_frontend_url:
			origins.add(self.vercel_frontend_url.strip())
		return sorted(origin for origin in origins if origin)

	def has_supabase_storage(self) -> bool:
		return bool(self.supabase_url and self.supabase_service_role_key and self.supabase_storage_bucket)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()
