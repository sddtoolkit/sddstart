"""handlers 映射校验测试。"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.handlers import REQUIRED_HANDLER_KEYS, build_default_handlers, build_handler_map  # noqa: E402


def _ok(_: argparse.Namespace) -> int:
    return 0


class CommandHandlersTests(unittest.TestCase):
    """覆盖命令处理映射的完整性校验。"""

    def test_build_handler_map_success(self) -> None:
        handlers = {key: _ok for key in REQUIRED_HANDLER_KEYS}
        mapped = build_handler_map(handlers)
        self.assertEqual(set(mapped.keys()), set(REQUIRED_HANDLER_KEYS))

    def test_build_handler_map_missing_key(self) -> None:
        handlers = {key: _ok for key in REQUIRED_HANDLER_KEYS if key != "check-drift"}
        with self.assertRaises(KeyError):
            build_handler_map(handlers)

    def test_build_default_handlers_complete(self) -> None:
        handlers = build_default_handlers()
        self.assertEqual(set(handlers.keys()), set(REQUIRED_HANDLER_KEYS))


if __name__ == "__main__":
    unittest.main()
