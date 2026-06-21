"""Logging setup for command-line tools, solvers, and experiments."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int | str = "INFO", logger_name: str | None = None) -> logging.Logger:
    """Configure process-wide logging and return the requested logger."""

    resolved_level = _resolve_level(level)
    logging.basicConfig(
        level=resolved_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stderr,
        force=True,
    )
    logger = logging.getLogger(logger_name)
    logger.setLevel(resolved_level)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger without changing global logging configuration."""

    return logging.getLogger(name)


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level

    resolved = logging.getLevelName(level.upper())
    if isinstance(resolved, int):
        return resolved
    raise ValueError(f"Unknown log level: {level}")
