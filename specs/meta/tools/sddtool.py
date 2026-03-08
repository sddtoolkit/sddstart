#!/usr/bin/env python3
"""SDD 工具入口脚本，负责转发到 CLI 主流程。"""

from __future__ import annotations

import sys

# Project-local setting: disable bytecode cache generation for tool runs.
sys.dont_write_bytecode = True

from sdd.cli import run_main


if __name__ == "__main__":
    sys.exit(run_main())
