"""
utils/logger.py
---------------
One place to configure logging for the whole project.

Usage in any module:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")

WHY logging instead of print()?
    - Log lines carry a timestamp, level (INFO/ERROR) and module name.
    - You can turn them up/down without editing code.
    - It is the professional standard and is expected in real projects.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a console handler (configured only once)."""
    logger = logging.getLogger(name)

    # Streamlit re-runs the script on every interaction. Without this check we
    # would attach a NEW handler each time and print every line many times.
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # don't send the same record to the root logger

    return logger
