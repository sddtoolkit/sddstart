"""Tests for Agent/Skill dispatch rule generation and resolution."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.generators.agentdispatchgenerator import (  # noqa: E402
    build_agent_dispatch_payload,
    resolve_agent_dispatch,
    write_agent_dispatch_file,
)


class AgentDispatchTests(unittest.TestCase):
    """Covers dispatch rule construction and routing results."""

    def test_build_payload_and_resolving(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            (specs_dir / "meta/agents").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/skills").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/index").mkdir(parents=True, exist_ok=True)

            (specs_dir / "meta/agents/agents.md").write_text(
                "\n".join(
                    [
                        "# Agent Role Definitions",
                        "",
                        "## Agent and Skill Relationships",
                        "| Agent | Primary Stage | Typical Skills | Responsibility Boundary (Not Responsible For) |",
                        "|---|---|---|---|",
                        "| orchestrator-agent | Orchestration and Advancement | check-traceability-skill, request-decision-skill | Does not replace professional review |",
                        "| specifier-agent | Requirements Clarification and Writing | clarify-requirements-skill, write-requirements-skill | Does not replace implementation decisions |",
                        "| reviewer-agent | Independent Auditing | check-traceability-skill | Does not replace implementation |",
                        "",
                        "## Shared Skill Arbitration Rules",
                        "- `check-traceability-skill`: orchestrator-agent used for process advancement, reviewer-agent used for independent auditing.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (specs_dir / "meta/skills/skills.md").write_text("# Skills Usage List\n", encoding="utf-8")
            for name in [
                "check-traceability-skill.md",
                "request-decision-skill.md",
                "clarify-requirements-skill.md",
                "write-requirements-skill.md",
            ]:
                (specs_dir / "meta/skills" / name).write_text(f"# {name}\n", encoding="utf-8")

            payload, warnings, errors = build_agent_dispatch_payload(specs_dir)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertIn("orchestrator-agent", [row["agent"] for row in payload["agents"]])
            self.assertEqual(
                payload["skill_owners"]["check-traceability-skill"],
                ["orchestrator-agent", "reviewer-agent"],
            )

            result = resolve_agent_dispatch(
                payload=payload,
                task="Please clarify requirements and write requirement documents first",
                stage="Requirements Clarification",
                requested_skills=["clarify-requirements-skill"],
            )
            self.assertEqual(result["primary_agent"], "specifier-agent")
            self.assertIn("clarify-requirements-skill", result["recommended_skills"])

    def test_write_dispatch_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            (specs_dir / "meta/agents").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/skills").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/index").mkdir(parents=True, exist_ok=True)

            (specs_dir / "meta/agents/agents.md").write_text(
                "\n".join(
                    [
                        "# Agent Role Definitions",
                        "",
                        "## Agent and Skill Relationships",
                        "| Agent | Primary Stage | Typical Skills | Responsibility Boundary (Not Responsible For) |",
                        "|---|---|---|---|",
                        "| orchestrator-agent | Orchestration and Advancement | request-decision-skill | Does not replace professional review |",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (specs_dir / "meta/skills/skills.md").write_text("# Skills Usage List\n", encoding="utf-8")
            (specs_dir / "meta/skills/request-decision-skill.md").write_text("# request-decision-skill\n", encoding="utf-8")

            output_path, warnings, errors = write_agent_dispatch_file(specs_dir)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["defaults"]["fallback_agent"], "orchestrator-agent")


if __name__ == "__main__":
    unittest.main()
