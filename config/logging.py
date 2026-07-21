"""Logging configuration.

A single :func:`get_logger` used across services. Keeps stack traces out of the
UI (see §30) — user-facing errors are formatted separately; logs are for devs.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger("valuation_platform")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under ``valuation_platform``."""
    _configure_root()
    return logging.getLogger(f"valuation_platform.{name}")
