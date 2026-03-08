#!/usr/bin/env python3
"""SDD 工具日志模块。"""

from __future__ import annotations

import sys


# Color constants for better CLI readability
COLOR_RESET = "\033[0m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"


def log_info(message: str) -> None:
    """输出普通信息（标准输出）。"""
    print(f"{COLOR_BLUE}[INFO]{COLOR_RESET} {message}")


def log_warning(message: str) -> None:
    """输出警告信息（标准错误）。"""
    print(f"{COLOR_YELLOW}[WARN]{COLOR_RESET} {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """输出错误信息（标准错误）。"""
    print(f"{COLOR_RED}[ERR ]{COLOR_RESET} {message}", file=sys.stderr)
