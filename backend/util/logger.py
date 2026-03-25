from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

from backend.core.config import get_settings


class JsonFormatter(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		payload: dict[str, Any] = {
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		for attr in (
			"request_id",
			"path",
			"method",
			"latency_ms",
			"job_id",
			"step",
			"attempt",
			"status",
			"model",
			"stdout",
			"stderr",
			"ci_status",
			"commit_sha",
		):
			if hasattr(record, attr):
				payload[attr] = getattr(record, attr)
		if record.exc_info:
			payload["exception"] = self.formatException(record.exc_info)
		return json.dumps(payload, default=str)


_configured = False


def configure_logging() -> None:
	global _configured
	if _configured:
		return

	settings = get_settings()

	root = logging.getLogger()
	root.setLevel(settings.log_level.upper())
	root.handlers.clear()

	formatter = JsonFormatter()

	stream = logging.StreamHandler()
	stream.setFormatter(formatter)

	root.addHandler(stream)

	if settings.log_to_file:
		os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
		rotating = RotatingFileHandler(settings.log_file, maxBytes=2_000_000, backupCount=5)
		rotating.setFormatter(formatter)
		root.addHandler(rotating)
	_configured = True


def get_logger(name: str) -> logging.Logger:
	configure_logging()
	return logging.getLogger(name)
