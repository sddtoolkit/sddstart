#!/usr/bin/env python3
"""Main CLI for SDD, responsible for command dispatching."""

from __future__ import annotations

import argparse
import sys

from sdd.commands.registry import register_commands
from sdd.handlers import build_default_handlers
from sdd.utils import resolve_safe_path, validate_semver, validate_slug


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser and register all subcommands."""
    parser = argparse.ArgumentParser(description="SDD Cross-platform Tool")
    subparsers = parser.add_subparsers(dest="command")
    register_commands(subparsers, build_default_handlers())
    return parser


def run_main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI: parses arguments and executes commands."""
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
