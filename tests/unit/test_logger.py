import logging

from src.shared.logger import setup_logger


def test_setup_logger():
    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
