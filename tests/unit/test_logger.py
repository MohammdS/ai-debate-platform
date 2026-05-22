import logging
from pathlib import Path

from src.shared.logger import LineRotatingFileHandler, setup_logger

# --- basic setup ---

def test_setup_logger():
    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO


def test_setup_logger_idempotent():
    a = setup_logger("idem_logger")
    b = setup_logger("idem_logger")
    assert a is b
    assert len(a.handlers) == len(b.handlers)


# --- LineRotatingFileHandler ---

def test_no_rotation_before_limit(tmp_path):
    log_file = tmp_path / "test.log"
    handler = LineRotatingFileHandler(log_file, max_lines=5, max_files=3)
    logger = _make_logger("no_rot", handler)

    for _ in range(4):
        logger.info("line")

    assert log_file.exists()
    assert not Path(f"{log_file}.1").exists()
    handler.close()


def test_rotation_after_limit(tmp_path):
    log_file = tmp_path / "test.log"
    handler = LineRotatingFileHandler(log_file, max_lines=3, max_files=5)
    logger = _make_logger("rot", handler)

    for i in range(6):
        logger.info("line %d", i)

    assert log_file.exists()
    assert Path(f"{log_file}.1").exists()
    handler.close()


def test_line_count_resets_after_rotation(tmp_path):
    log_file = tmp_path / "test.log"
    handler = LineRotatingFileHandler(log_file, max_lines=3, max_files=5)

    for _ in range(3):
        handler._line_count += 1
    assert handler.shouldRollover(None)

    handler.doRollover()
    assert handler._line_count == 0
    assert not handler.shouldRollover(None)
    handler.close()


def test_fifo_max_files_enforced(tmp_path):
    log_file = tmp_path / "test.log"
    max_files = 3
    handler = LineRotatingFileHandler(log_file, max_lines=1, max_files=max_files)
    logger = _make_logger("fifo", handler)

    # Write enough lines to trigger many rotations
    for i in range(10):
        logger.info("msg %d", i)

    rotated = list(tmp_path.glob("test.log.*"))
    assert len(rotated) <= max_files
    handler.close()


def test_log_directory_created(tmp_path):
    nested = tmp_path / "a" / "b" / "debate.log"
    handler = LineRotatingFileHandler(nested, max_lines=10, max_files=3)
    assert nested.parent.exists()
    handler.close()


# --- helpers ---

def _make_logger(name: str, handler: logging.Handler) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger
