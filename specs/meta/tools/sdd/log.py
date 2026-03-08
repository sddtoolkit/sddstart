#!/usr/bin/env python3
"""Logging module for SDD tools."""

from __future__ import annotations

import sys


# Color constants for better CLI readability
COLOR_RESET = "\033[0m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"


def log_info(message: str) -> None:
    """Print informational message (standard output)."""
    print(f"{COLOR_BLUE}[INFO]{COLOR_RESET} {message}")


def log_warning(message: str) -> None:
    """Print warning message (standard error)."""
    print(f"{COLOR_YELLOW}[WARN]{COLOR_RESET} {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Print error message (standard error)."""
    print(f"{COLOR_RED}[ERR ]{COLOR_RESET} {message}", file=sys.stderr)
