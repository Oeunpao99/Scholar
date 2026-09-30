"""Logging configuration for the API process."""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return str(payload)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.is_production:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    _CONFIGURED = True
