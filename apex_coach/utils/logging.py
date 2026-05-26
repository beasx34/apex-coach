"""Lightweight structured logging setup."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger for the apex-coach app.

    Idempotent — safe to call multiple times.
    """
    root = logging.getLogger()
    if getattr(root, "_apex_coach_configured", False):
        return
    root.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.handlers[:] = [handler]
    root._apex_coach_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""
    return logging.getLogger(f"apex_coach.{name}")
