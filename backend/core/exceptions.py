from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.logger import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            extra={
                "request_id": getattr(request.state, "request_id", "n/a"),
                "path": request.url.path,
                "method": request.method,
                "status": exc.status_code,
            },
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error",
            extra={
                "request_id": getattr(request.state, "request_id", "n/a"),
                "path": request.url.path,
                "method": request.method,
                "status": 500,
            },
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
