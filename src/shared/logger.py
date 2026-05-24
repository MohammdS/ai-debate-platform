from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from src.shared.config import ConfigManager


def _load_log_config() -> tuple[str, int, int]:
    """Returns (log_dir, max_lines_per_file, max_files) from setup.json."""
    try:
        cfg = ConfigManager()
        return (
            cfg.get_value("logs", "log_dir", "logs"),
            cfg.get_value("logs", "max_lines_per_file", 500),
            cfg.get_value("logs", "max_files", 20),
        )
    except Exception:
        return ("logs", 500, 20)


class LineRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """
    FIFO rotating handler: rotates after max_lines lines.
    Keeps at most max_files log files — oldest deleted when limit exceeded.
    File naming: debate.log, debate.log.1, debate.log.2, ...
    """

    def __init__(self, filepath: Path, max_lines: int, max_files: int):
        self.filepath = filepath
        self.max_lines = max_lines
        self.max_files = max_files
        self._line_count = 0
        filepath.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(str(filepath), mode="a", encoding="utf-8", delay=False)

    def shouldRollover(self, record: logging.LogRecord) -> bool:  # noqa: N802
        return self._line_count >= self.max_lines

    def doRollover(self) -> None:  # noqa: N802
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]

        # Shift existing rotated files: .N → .(N+1), delete if > max_files
        for i in range(self.max_files - 1, 0, -1):
            src = Path(f"{self.filepath}.{i}")
            dst = Path(f"{self.filepath}.{i + 1}")
            if dst.exists():
                dst.unlink()
            if src.exists():
                src.rename(dst)

        # Rotate current file → .1
        rotated = Path(f"{self.filepath}.1")
        if rotated.exists():
            rotated.unlink()
        if self.filepath.exists():
            self.filepath.rename(rotated)

        # Enforce FIFO: remove files beyond max_files
        for i in range(self.max_files + 1, self.max_files + 10):
            old = Path(f"{self.filepath}.{i}")
            if old.exists():
                old.unlink()

        self._line_count = 0
        self.stream = self._open()

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self._line_count += 1


def setup_logger(name: str = "ai_debate") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    log_dir, max_lines, max_files = _load_log_config()
    log_path = Path(log_dir) / "debate.log"
    fh = LineRotatingFileHandler(log_path, max_lines=max_lines, max_files=max_files)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
