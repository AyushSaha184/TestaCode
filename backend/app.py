from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.bootstrap import get_repository
from backend.core.config import get_settings
from backend.core.exceptions import install_exception_handlers
from backend.util.logger import configure_logging, get_logger
from backend.core.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
	settings = get_settings()
	settings.validate_production_configuration()
	configure_logging()
	app = FastAPI(title=settings.app_name)

	app.add_middleware(RequestContextMiddleware)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=settings.cors_origins(),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	install_exception_handlers(app)
	app.include_router(router)

	logger = get_logger(__name__)

	@app.get("/health")
	def health() -> dict[str, str]:
		repo = get_repository()
		repo.healthcheck()
		logger.info("healthcheck_ok", extra={"step": "health", "status": "ok"})
		return {"status": "ok"}

	return app


app = create_app()
