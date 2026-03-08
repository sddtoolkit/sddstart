"""Tests for req/design validator behavior."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.validators.designvalidator import check_design_file  # noqa: E402
from sdd.validators.reqvalidator import check_requirement_file  # noqa: E402


class ValidatorsTests(unittest.TestCase):
    """Covers validation of requirement and design document sections."""

    def test_requirement_validator_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            req_path = Path(tmp_dir) / "requirements.md"
            req_path.write_text(
                "\n".join(
                    [
                        "# Requirement Specification",
                        "## Meta Information",
                        "- Document ID: req-baseline-001",
                        "- Version: v1.0",
                        "- Owner: specifier-agent",
                        "- Date: 2026-03-02",
                        "## Goals and Scope",
                        "- Goal: Define template project capability boundaries",
                        "- Scope: spec and toolchain",
                        "## Functional Requirements",
                        "- FR-1: Should support full traceability",
                        "## Acceptance Criteria",
                        "- AC-1: Traceability matrix includes req/design/task/test",
                        "## Traceability",
                        "- Related Design: dsn-baseline-architecture",
                        "- Related Task: tsk-baseline-001",
                        "- Related Test: test-baseline-001",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_requirement_file(req_path), 0)

            req_path.write_text(
                "# Requirement Specification\n## Meta Information\n- Document ID: req-baseline-001\n- Version: \n## Goals and Scope\n## Functional Requirements\n## Acceptance Criteria\n## Traceability\n",
                encoding="utf-8",
            )
            self.assertEqual(check_requirement_file(req_path), 1)

    def test_design_validator_pass_with_alternative_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            design_path = Path(tmp_dir) / "architecture.md"
            design_path.write_text(
                "\n".join(
                    [
                        "# Architecture Design",
                        "## Meta Information",
                        "- Document ID: dsn-baseline-architecture",
                        "- Version: v1.0",
                        "- Owner: architect-agent",
                        "- Date: 2026-03-02",
                        "## Security and Privacy",
                        "- Auth: Use repository minimum privilege policy",
                        "- Data Protection: All documents UTF-8 encoded",
                        "## Reliability and Performance",
                        "- Performance Goal: Validation command completes within 5 seconds",
                        "## Traceability",
                        "- Related Requirement: req-baseline-001",
                        "- Related Task: tsk-baseline-001",
                        "## System Boundaries",
                        "- Boundary Definition: Only process specs directory",
                        "- External Dependencies: Python standard library",
                        "## Interfaces and Contracts",
                        "- External Interface: python3 specs/meta/tools/sddtool.py <subcommand>",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_design_file(design_path), 0)

    def test_design_validator_fail_without_alternative_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            design_path = Path(tmp_dir) / "architecture.md"
            design_path.write_text(
                "\n".join(
                    [
                        "# Architecture Design",
                        "## Meta Information",
                        "## Security and Privacy",
                        "## Reliability and Performance",
                        "## Traceability",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_design_file(design_path), 1)


if __name__ == "__main__":
    unittest.main()
