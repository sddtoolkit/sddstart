"""Agent/Skill 调度规则生成与解析测试。"""

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
    """覆盖调度规则构建与路由结果。"""

    def test_build_payload_and_resolving(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir)
            (specs_dir / "meta/agents").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/skills").mkdir(parents=True, exist_ok=True)
            (specs_dir / "meta/index").mkdir(parents=True, exist_ok=True)

            (specs_dir / "meta/agents/agents.md").write_text(
                "\n".join(
                    [
                        "# Agent 角色定义",
                        "",
                        "## Agent 与 Skill 对应关系",
                        "| Agent | 主责阶段 | 典型使用 Skill | 责任边界（不负责） |",
                        "|---|---|---|---|",
                        "| orchestrator-agent | 编排与推进 | check-traceability-skill, request-decision-skill | 不替代专业评审 |",
                        "| specifier-agent | 需求澄清与编写 | clarify-requirements-skill, write-requirements-skill | 不替代实现决策 |",
                        "| reviewer-agent | 独立审计 | check-traceability-skill | 不替代实施 |",
                        "",
                        "## 共享 Skill 仲裁规则",
                        "- `check-traceability-skill`：orchestrator-agent 用于流程推进，reviewer-agent 用于独立审计。",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (specs_dir / "meta/skills/skills.md").write_text("# Skills 使用清单\n", encoding="utf-8")
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
                task="请先做需求澄清并编写需求文档",
                stage="需求澄清",
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
                        "# Agent 角色定义",
                        "",
                        "## Agent 与 Skill 对应关系",
                        "| Agent | 主责阶段 | 典型使用 Skill | 责任边界（不负责） |",
                        "|---|---|---|---|",
                        "| orchestrator-agent | 编排与推进 | request-decision-skill | 不替代专业评审 |",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (specs_dir / "meta/skills/skills.md").write_text("# Skills 使用清单\n", encoding="utf-8")
            (specs_dir / "meta/skills/request-decision-skill.md").write_text("# request-decision-skill\n", encoding="utf-8")

            output_path, warnings, errors = write_agent_dispatch_file(specs_dir)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["defaults"]["fallback_agent"], "orchestrator-agent")


if __name__ == "__main__":
    unittest.main()
