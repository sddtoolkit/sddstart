"""完整性检查器关键行为测试。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.checkers.completenesschecker import check_completeness  # noqa: E402


class CompletenessCheckerTests(unittest.TestCase):
    """覆盖空矩阵与最小有效矩阵行为。"""

    def test_empty_matrix_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            index_dir = specs_dir / "meta/index"
            index_dir.mkdir(parents=True, exist_ok=True)
            (index_dir / "traceability.json").write_text("{}\n", encoding="utf-8")

            self.assertEqual(check_completeness(specs_dir), 1)

    def test_minimum_required_links_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            index_dir = specs_dir / "meta/index"
            index_dir.mkdir(parents=True, exist_ok=True)
            (specs_dir / "1-reqs").mkdir(parents=True, exist_ok=True)
            (specs_dir / "adrs").mkdir(parents=True, exist_ok=True)
            (specs_dir / "2-designs").mkdir(parents=True, exist_ok=True)
            (specs_dir / "3-tasks").mkdir(parents=True, exist_ok=True)
            (specs_dir / "tests").mkdir(parents=True, exist_ok=True)

            (specs_dir / "1-reqs/requirements.md").write_text("rq-baseline-001\n", encoding="utf-8")
            (specs_dir / "adrs/adr-20260302-baseline-governance.md").write_text(
                "adr-20260302-baseline-governance\n", encoding="utf-8"
            )
            (specs_dir / "2-designs/architecture.md").write_text("ds-baseline-architecture\n", encoding="utf-8")
            (specs_dir / "3-tasks/task-20260302-baseline-001.md").write_text(
                "tk-baseline-001\n", encoding="utf-8"
            )
            (specs_dir / "tests/test-baseline-001.md").write_text("test-baseline-001\n", encoding="utf-8")

            matrix = {
                "RQ-BASELINE-001": {
                    "adrs": ["ADR-20260302-BASELINE-GOVERNANCE"],
                    "designs": ["DS-BASELINE-ARCHITECTURE"],
                    "tasks": ["TK-BASELINE-001"],
                    "tests": ["TEST-BASELINE-001"],
                    "implementations": ["src/main.py"],
                }
            }
            (index_dir / "traceability.json").write_text(json.dumps(matrix, ensure_ascii=False) + "\n", encoding="utf-8")

            self.assertEqual(check_completeness(specs_dir), 0)

    def test_missing_linked_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            index_dir = specs_dir / "meta/index"
            index_dir.mkdir(parents=True, exist_ok=True)
            (specs_dir / "1-reqs").mkdir(parents=True, exist_ok=True)
            (specs_dir / "2-designs").mkdir(parents=True, exist_ok=True)
            (specs_dir / "3-tasks").mkdir(parents=True, exist_ok=True)
            (specs_dir / "tests").mkdir(parents=True, exist_ok=True)
            (specs_dir / "adrs").mkdir(parents=True, exist_ok=True)

            (specs_dir / "1-reqs/requirements.md").write_text("rq-baseline-001\n", encoding="utf-8")
            matrix = {
                "RQ-BASELINE-001": {
                    "adrs": ["ADR-NOT-EXISTS"],
                    "designs": ["DS-NOT-EXISTS"],
                    "tasks": ["TK-NOT-EXISTS"],
                    "tests": ["TEST-NOT-EXISTS"],
                    "implementations": [],
                }
            }
            (index_dir / "traceability.json").write_text(json.dumps(matrix, ensure_ascii=False) + "\n", encoding="utf-8")

            self.assertEqual(check_completeness(specs_dir), 1)


if __name__ == "__main__":
    unittest.main()
