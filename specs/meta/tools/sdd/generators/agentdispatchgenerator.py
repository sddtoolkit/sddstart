"""
Agent/Skill 统一调度规则生成与解析。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| Agent权威映射 | agents.md | Agent定义 |
| Skill权威清单 | skills.md | Skill定义 |
| 调度契约 | agent-dispatch.json | 调度规则 |
| Agent协作宪章 | G05 | 统一调度 |

### agents.md 定义
- Agent 命名规范：`xxx-agent` 格式
- Agent 与 Skill 的对应关系
- Agent 主责阶段定义

### skills.md 定义
- Skill 命名规范：`xxx-skill` 格式
- Skill 能力描述
- Skill 使用场景

### agent-dispatch.json 契约
- 调度载荷结构定义
- Agent 优先级计算规则
- 共享 Skill 仲裁规则

### G05-Agent协作宪章 要求
- 所有工具必须通过 agent-dispatch.json 调度
- Agent 解析必须基于统一规则
- 冲突通过 shared_skill_arbitration 仲裁

## 实现映射

| 函数 | 规范要求 | 规范来源 |
|------|----------|----------|
| `parse_agent_skill_rows()` | 解析Agent映射表 | agents.md |
| `parse_shared_skill_rules()` | 解析共享Skill规则 | agents.md |
| `build_agent_dispatch_payload()` | 构建调度载荷 | agent-dispatch.json |
| `resolve_agent_dispatch()` | 解析任务调度 | G05-统一调度 |

参见：
- specs/meta/agents/agents.md
- specs/meta/skills/skills.md
- specs/meta/index/agent-dispatch.json
- specs/govs/G05-Agent协作宪章.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sdd.io import read_text_safe
from sdd.utils import extract_md_section
from sdd.log import log_info, log_warning, log_error

# 规范引用：agents.md - Agent 标识模式
AGENT_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*-agent")

# 规范引用：skills.md - Skill 标识模式
SKILL_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*-skill")


def _splitting_markdown_row(raw_line: str) -> list[str]:
    """将 Markdown 表格行切分为单元格列表。"""
    text = raw_line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        return []
    return [cell.strip() for cell in text.strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """判断是否为 Markdown 表格分隔行（---）。"""
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None for cell in cells)


def _extract_skill_ids(text: str) -> list[str]:
    """从文本中提取所有 skill 标识。"""
    return sorted(set(SKILL_PATTERN.findall(text.lower())))


def _extract_agent_ids(text: str) -> list[str]:
    """从文本中提取所有 agent 标识。"""
    return sorted(set(AGENT_PATTERN.findall(text.lower())))


def parse_agent_skill_rows(agents_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """解析 `Agent 与 Skill 对应关系` 表格。"""
    section_lines = extract_md_section(agents_text, "Agent 与 Skill 对应关系")
    table_lines = [line.strip() for line in section_lines if line.strip().startswith("|")]

    if len(table_lines) < 3:
        return [], ["缺少 Agent 与 Skill 对应关系表格"]

    header = _splitting_markdown_row(table_lines[0])
    if not header:
        return [], ["Agent 与 Skill 对应关系表头解析失败"]

    required_columns = {"Agent", "主责阶段", "典型使用 Skill"}
    if not required_columns.issubset(set(header)):
        return [], [f"Agent 与 Skill 对应关系表头缺少字段：{sorted(required_columns - set(header))}"]

    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for raw_line in table_lines[1:]:
        cells = _splitting_markdown_row(raw_line)
        if not cells:
            continue
        if _is_separator_row(cells):
            continue
        if len(cells) != len(header):
            issues.append(f"Agent 表格列数不一致：{raw_line}")
            continue

        record = dict(zip(header, cells))
        agent = record.get("Agent", "").strip().strip("`")
        if not AGENT_PATTERN.fullmatch(agent):
            matched_agents = _extract_agent_ids(agent)
            if not matched_agents:
                issues.append(f"Agent 名称非法：{record.get('Agent', '')}")
                continue
            agent = matched_agents[0]

        skills = _extract_skill_ids(record.get("典型使用 Skill", ""))
        if not skills:
            issues.append(f"{agent} 未声明可用 Skill")
            continue

        rows.append(
            {
                "agent": agent,
                "stage": record.get("主责阶段", "").strip(),
                "skills": skills,
                "not_responsible": record.get("责任边界（不负责）", "").strip(),
            }
        )

    if not rows:
        issues.append("未解析到任何 Agent 行")
    return rows, issues


def parse_shared_skill_rules(agents_text: str) -> list[dict[str, Any]]:
    """解析 `共享 Skill 仲裁规则` 章节。"""
    section_lines = extract_md_section(agents_text, "共享 Skill 仲裁规则")
    rows: list[dict[str, Any]] = []
    for line in section_lines:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue

        skill_match = SKILL_PATTERN.search(stripped.lower())
        if skill_match is None:
            continue
        skill = skill_match.group(0)
        agents = _extract_agent_ids(stripped)
        rows.append(
            {
                "skill": skill,
                "agents": agents,
                "rule": stripped.lstrip("-").strip(),
            }
        )
    return rows


def _collect_skill_catalog(specs_dir: Path) -> list[str]:
    """读取 `meta/skills/` 目录中实际存在的 Skill 文件清单。"""
    return sorted(path.stem for path in (specs_dir / "meta/skills").glob("*-skill.md"))


def build_agent_dispatch_payload(specs_dir: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    """构建统一调度载荷，并返回 (payload, warnings, errors)。"""
    agents_path = specs_dir / "meta/agents/agents.md"
    skills_path = specs_dir / "meta/skills/skills.md"

    warnings: list[str] = []
    errors: list[str] = []

    if not agents_path.exists():
        errors.append(f"缺少 Agent 权威映射文档：{agents_path}")
        return {}, warnings, errors
    if not skills_path.exists():
        errors.append(f"缺少 Skill 清单文档：{skills_path}")
        return {}, warnings, errors

    agents_text = read_text_safe(agents_path)
    agent_rows, row_issues = parse_agent_skill_rows(agents_text)
    if row_issues:
        errors.extend(row_issues)

    shared_rules = parse_shared_skill_rules(agents_text)
    skill_catalog = _collect_skill_catalog(specs_dir)
    skill_catalog_set = set(skill_catalog)

    skill_owners: dict[str, set[str]] = {}
    for row in agent_rows:
        agent = row["agent"]
        for skill in row["skills"]:
            skill_owners.setdefault(skill, set()).add(agent)
            if skill not in skill_catalog_set:
                errors.append(f"Agent 映射引用了不存在的 Skill 文件：{skill}")

    for item in shared_rules:
        skill = item["skill"]
        if skill not in skill_catalog_set:
            warnings.append(f"共享 Skill 仲裁规则引用了未落盘 Skill：{skill}")
        for agent in item["agents"]:
            skill_owners.setdefault(skill, set()).add(agent)

    for skill in skill_catalog:
        if skill not in skill_owners:
            warnings.append(f"Skill 未绑定主责 Agent：{skill}")

    payload: dict[str, Any] = {
        "meta": {
            "schema": "sdd.agent-dispatch.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "agents": "specs/meta/agents/agents.md",
                "skills": "specs/meta/skills/skills.md",
            },
        },
        "agents": agent_rows,
        "skill_catalog": skill_catalog,
        "skill_owners": {skill: sorted(owners) for skill, owners in sorted(skill_owners.items())},
        "shared_skill_arbitration": shared_rules,
        "defaults": {
            "fallback_agent": "orchestrator-agent",
            "decision_skill": "request-decision-skill",
        },
    }
    return payload, warnings, errors


def write_agent_dispatch_file(specs_dir: Path) -> tuple[Path, list[str], list[str]]:
    """写入统一调度规则 JSON 文件。"""
    payload, warnings, errors = build_agent_dispatch_payload(specs_dir)
    target = specs_dir / "meta/index/agent-dispatch.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target, warnings, errors


def _matching_stage_score(stage_query: str, stage_text: str) -> int:
    """计算输入阶段与 Agent 主责阶段文本的匹配分。"""
    if not stage_query:
        return 0

    query = stage_query.strip().lower()
    stage = stage_text.strip().lower()
    if not query or not stage:
        return 0
    if query in stage or stage in query:
        return 4

    score = 0
    for token in re.split(r"[,\s/|+、，；;]+", stage):
        key = token.strip()
        if len(key) >= 2 and key in query:
            score += 1
    return score


KEYWORD_AGENT_MAP: dict[str, str] = {
    "需求": "specifier-agent",
    "requirement": "specifier-agent",
    "设计": "architect-agent",
    "design": "architect-agent",
    "架构": "architect-agent",
    "architecture": "architect-agent",
    "规划": "planner-agent",
    "任务": "planner-agent",
    "task": "planner-agent",
    "测试": "tester-agent",
    "test": "tester-agent",
    "发布": "release-agent",
    "release": "release-agent",
    "代码": "developer-agent",
    "code": "developer-agent",
    "实现": "developer-agent",
    "implement": "developer-agent",
    "审查": "reviewer-agent",
    "review": "reviewer-agent",
    "评审": "reviewer-agent",
    "运维": "release-agent",
    "ops": "release-agent",
    "部署": "release-agent",
    "deploy": "release-agent",
}


def _normalizing_requested_skills(raw_skills: list[str] | None) -> list[str]:
    """归一化命令行传入的 skill 列表参数。"""
    if not raw_skills:
        return []
    merged = ",".join(raw_skills)
    return sorted(set(SKILL_PATTERN.findall(merged.lower())))


def resolve_agent_dispatch(
    payload: dict[str, Any],
    task: str,
    stage: str | None = None,
    requested_skills: list[str] | None = None,
) -> dict[str, Any]:
    """根据统一映射解析任务调度建议。"""
    agents = payload.get("agents", [])
    fallback_agent = payload.get("defaults", {}).get("fallback_agent", "orchestrator-agent")
    skill_owners = payload.get("skill_owners", {})
    shared_rules = payload.get("shared_skill_arbitration", [])

    query = task.strip().lower()
    stage_query = (stage or "").strip().lower()
    skill_hints = _normalizing_requested_skills(requested_skills)

    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}

    for row in agents:
        agent = row.get("agent", "")
        if not agent:
            continue
        score = 0
        why: list[str] = []

        stage_score = _matching_stage_score(stage_query, row.get("stage", ""))
        if stage_score > 0:
            score += stage_score
            why.append(f"阶段匹配 +{stage_score}")

        for skill in row.get("skills", []):
            if skill in skill_hints:
                score += 5
                why.append(f"Skill 指定 {skill} +5")
            skill_token = skill.removesuffix("-skill").replace("-", " ")
            if skill_token and skill_token in query:
                score += 2
                why.append(f"任务命中 Skill 关键词 {skill} +2")

        if agent in query:
            score += 2
            why.append("任务显式提及 Agent +2")

        if score > 0:
            scores[agent] = score
            reasons[agent] = why

    for keyword, mapped_agent in KEYWORD_AGENT_MAP.items():
        if keyword in query and mapped_agent not in scores:
            scores[mapped_agent] = 3
            reasons[mapped_agent] = [f"关键词匹配 '{keyword}' → {mapped_agent} +3"]

    if not scores:
        primary_agent = fallback_agent
        primary_score = 0
        primary_reasons = ["未命中显式规则，使用默认 orchestrator 调度"]
    else:
        ranking = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        primary_agent, primary_score = ranking[0]
        primary_reasons = reasons.get(primary_agent, [])

    primary_row: dict = next((row for row in agents if row.get("agent") == primary_agent), {})
    recommended_skills = skill_hints or list(primary_row.get("skills", []))

    support_agents: set[str] = set()
    for skill in recommended_skills:
        for owner in skill_owners.get(skill, []):
            if owner != primary_agent:
                support_agents.add(owner)

    arbitration = [rule for rule in shared_rules if rule.get("skill") in recommended_skills]
    result = {
        "task": task,
        "stage": stage or "",
        "requested_skills": skill_hints,
        "primary_agent": primary_agent,
        "primary_score": primary_score,
        "primary_reasons": primary_reasons,
        "recommended_skills": recommended_skills,
        "support_agents": sorted(support_agents),
        "shared_skill_arbitration": arbitration,
        "fallback_agent": fallback_agent,
    }
    return result


__all__ = [
    "build_agent_dispatch_payload",
    "parse_agent_skill_rows",
    "parse_shared_skill_rules",
    "resolve_agent_dispatch",
    "write_agent_dispatch_file",
]
