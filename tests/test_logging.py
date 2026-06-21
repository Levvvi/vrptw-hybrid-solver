import logging

import pytest

from vrptw_hybrid.utils.logging import DATE_FORMAT, LOG_FORMAT, get_logger, setup_logging


def test_setup_logging_returns_named_logger() -> None:
    logger = setup_logging("DEBUG", "vrptw_hybrid.test")

    assert logger.name == "vrptw_hybrid.test"
    assert logger.level == logging.DEBUG
    assert logging.getLogger().level == logging.DEBUG


def test_log_format_contains_required_fields() -> None:
    assert "%(asctime)s" in LOG_FORMAT
    assert "%(name)s" in LOG_FORMAT
    assert "%(levelname)s" in LOG_FORMAT
    assert "%(message)s" in LOG_FORMAT
    assert DATE_FORMAT == "%Y-%m-%d %H:%M:%S"


def test_get_logger_does_not_require_setup() -> None:
    logger = get_logger("vrptw_hybrid.module")

    assert logger.name == "vrptw_hybrid.module"


def test_unknown_log_level_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unknown log level"):
        setup_logging("LOUD")
