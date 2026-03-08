"""依赖检查器关键边界测试。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.checkers import dependencychecker  # noqa: E402


class DependencyCheckerTests(unittest.TestCase):
    """覆盖 requirements include 深度保护。"""

    def test_requirements_include_depth_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            chain_length = dependencychecker.MAX_REQUIREMENT_INCLUDE_DEPTH + 3

            for idx in range(chain_length):
                current = root / f"req-{idx}.txt"
                if idx + 1 < chain_length:
                    current.write_text(f"-r req-{idx + 1}.txt\n", encoding="utf-8")
                else:
                    current.write_text("requests==2.32.0\n", encoding="utf-8")

            warnings: list[str] = []
            entries = dependencychecker._iterate_requirement_entries(root / "req-0.txt", warnings, set())

            self.assertTrue(any("include 嵌套超过最大深度" in warning for warning in warnings))
            self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
