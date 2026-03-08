#!/usr/bin/env python3
"""SDD 工具主 CLI，负责命令分发。"""

from __future__ import annotations

import argparse
import sys

from sdd.commands.registry import register_commands
from sdd.handlers import build_default_handlers
from sdd.utils import resolve_safe_path, validate_semver, validate_slug


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器并注册所有子命令。"""
    parser = argparse.ArgumentParser(description="SDD 跨平台工具")
    subparsers = parser.add_subparsers(dest="command")
    register_commands(subparsers, build_default_handlers())
    return parser


def run_main(argv: list[str] | None = None) -> int:
    """CLI 主入口：解析参数并执行命令。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "running"):
        parser.print_help()
        return 1

    return args.running(args)


__all__ = [
    "build_parser",
    "resolve_safe_path",
    "run_main",
    "validate_semver",
    "validate_slug",
]


if __name__ == "__main__":
    sys.exit(run_main())
