"""Logging configuration for the resume parser module."""

from __future__ import annotations

import logging
import sys
from typing import Literal


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> None:
    """
    Configure standard logging for the resume parser.

    Call this once at application startup if you want library logs visible.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger("resume_parser")

    if root_logger.handlers:
        root_logger.setLevel(log_level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    root_logger.propagate = False
