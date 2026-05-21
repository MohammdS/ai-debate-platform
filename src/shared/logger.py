import logging
import sys


def setup_logger(name: str = "ai_debate") -> logging.Logger:
    """Configures and returns a standard logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler
        fh = logging.FileHandler("debate.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
