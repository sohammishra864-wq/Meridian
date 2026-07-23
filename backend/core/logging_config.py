"""Structured JSON logging configuration."""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Format logs as JSON with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }

        # Add request context if available
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        # Add exception trace if present
        if record.exc_info:
            log_data['error_trace'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging() -> None:
    """Configure structured JSON logging for FastAPI."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

    # Configure uvicorn loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.propagate = False
