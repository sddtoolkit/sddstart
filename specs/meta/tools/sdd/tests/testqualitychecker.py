"""qualitychecker 注释解析边界测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.checkers.qualitychecker import (  # noqa: E402
    _check_todo_marker_in_comment,
    _extract_c_style_comment_fragment,
)


class QualityCheckerTests(unittest.TestCase):
    """覆盖 C 风格注释片段提取与 TODO 检测边界。"""

    def test_extracting_c_style_comment_fragment_inline_block(self) -> None:
        fragment, in_block = _extract_c_style_comment_fragment("const a = 1; /* TODO: fix */", False)
        self.assertIn("TODO", fragment)
        self.assertFalse(in_block)

    def test_extracting_c_style_comment_fragment_unclosed_block(self) -> None:
        fragment, in_block = _extract_c_style_comment_fragment("const a = 1; /* FIXME start", False)
        self.assertIn("FIXME", fragment)
        self.assertTrue(in_block)

    def test_extracting_c_style_comment_fragment_close_existing_block(self) -> None:
        fragment, in_block = _extract_c_style_comment_fragment("continue comment */ const a = 1;", True)
        self.assertIn("continue comment", fragment)
        self.assertFalse(in_block)

    def test_check_todo_marker_in_comment_python(self) -> None:
        has_todo, in_block = _check_todo_marker_in_comment("x = 1  # TODO later", ".py", False)
        self.assertTrue(has_todo)
        self.assertFalse(in_block)

        has_todo, in_block = _check_todo_marker_in_comment("print('TODO in string')", ".py", False)
        self.assertFalse(has_todo)
        self.assertFalse(in_block)

    def test_check_todo_marker_in_comment_c_style_multiline(self) -> None:
        has_todo, in_block = _check_todo_marker_in_comment("/* TODO begin", ".ts", False)
        self.assertTrue(has_todo)
        self.assertTrue(in_block)

        has_todo, in_block = _check_todo_marker_in_comment("continue comment */ const x = 1;", ".ts", in_block)
        self.assertFalse(has_todo)
        self.assertFalse(in_block)


if __name__ == "__main__":
    unittest.main()
