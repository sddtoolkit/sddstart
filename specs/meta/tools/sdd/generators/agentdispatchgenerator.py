"""
Unified Agent/Skill dispatch rule generation and parsing.

## Specification Reference

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Agent Authoritative Mapping | agents.md | Agent Definition |
| Skill Authoritative List | skills.md | Skill Definition |
| Dispatch Contract | agent-dispatch.json | Dispatch Rules |
| Agent Collaboration Charter | G05 | Unified Dispatch |

### agents.md Definition
- Agent naming convention: `xxx-agent` format
- Correspondence between Agents and Skills
- Agent primary responsibility stage definition

### skills.md Definition
- Skill naming convention: `xxx-skill` format
- Skill capability description
- Skill usage scenarios

### agent-dispatch.json Contract
- Dispatch payload structure definition
- Agent priority calculation rules
- Shared Skill arbitration rules

### G05-Agent Collaboration Charter Requirements
- All tools must be dispatched via agent-dispatch.json
- Agent parsing must be based on unified rules
- Conflicts are arbitrated via shared_skill_arbitration

## Implementation Mapping

| Function | Specification Requirement | Specification Source |
|------|----------|----------|
| `parse_agent_skill_rows()` | Parse Agent mapping table | agents.md |
| `parse_shared_skill_rules()` | Parse shared Skill rules | agents.md |
| `build_agent_dispatch_payload()` | Build dispatch payload | agent-dispatch.json |
| `resolve_agent_dispatch()` | Resolve task dispatch | G05-Unified Dispatch |

See:
- specs/meta/agents/agents.md
- specs/meta/skills/skills.md
- specs/meta/index/agent-dispatch.json
- specs/govs/G05-Agent Collaboration Charter.md
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

# Specification Reference: agents.md - Agent identification pattern
AGENT_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*-agent")

# Specification Reference: skills.md - Skill identification pattern
SKILL_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*-skill")


def _splitting_markdown_row(raw_line: str) -> list[str]:
    """Split a Markdown table row into a list of cells."""
    text = raw_line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        return []
    return [cell.strip() for cell in text.strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """Determine if a row is a Markdown table separator (---)."""
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None for cell in cells)


def _extract_skill_ids(text: str) -> list[str]:
    """Extract all skill identifiers from text."""
    return sorted(set(SKILL_PATTERN.findall(text.lower())))


def _extract_agent_ids(text: str) -> list[str]:
    """Extract all agent identifiers from text."""
    return sorted(set(AGENT_PATTERN.findall(text.lower())))


def parse_agent_skill_rows(agents_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse the 'Agent and Skill Correspondence' table."""
    section_lines = extract_md_section(agents_text, "Agent 与 Skill 对应关系")
    table_lines = [line.strip() for line in section_lines if line.strip().startswith("|")]

    if len(table_lines) < 3:
        return [], ["Missing Agent and Skill correspondence table"]

    header = _splitting_markdown_row(table_lines[0])
    if not header:
        return [], ["Failed to parse Agent and Skill correspondence table header"]

    required_columns = {"Agent", "主责阶段", "典型使用 Skill"}
    if not required_columns.issubset(set(header)):
        return [], [f"Agent and Skill correspondence table is missing fields: {sorted(required_columns - set(header))}"]

    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for raw_line in table_lines[1:]:
        cells = _splitting_markdown_row(raw_line)
        if not cells:
            continue
        if _is_separator_row(cells):
            continue
        if len(cells) != len(header):
            issues.append(f"Inconsistent column count in Agent table: {raw_line}")
            continue

        record = dict(zip(header, cells))
        agent = record.get("Agent", "").strip().strip("`")
        if not AGENT_PATTERN.fullmatch(agent):
            matched_agents = _extract_agent_ids(agent)
            if not matched_agents:
                issues.append(f"Invalid Agent name: {record.get('Agent', '')}")
                continue
            agent = matched_agents[0]

        skills = _extract_skill_ids(record.get("典型使用 Skill", ""))
        if not skills:
            issues.append(f"{agent} has no declared available Skills")
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
        issues.append("No Agent rows parsed")
    return rows, issues


def parse_shared_skill_rules(agents_text: str) -> list[dict[str, Any]]:
    """Parse the 'Shared Skill Arbitration Rules' section."""
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
    """Read the list of Skill files actually present in the 'meta/skills/' directory."""
    return sorted(path.stem for path in (specs_dir / "meta/skills").glob("*-skill.md"))


def build_agent_dispatch_payload(specs_dir: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build the unified dispatch payload and return (payload, warnings, errors)."""
    agents_path = specs_dir / "meta/agents/agents.md"
    skills_path = specs_dir / "meta/skills/skills.md"

    warnings: list[str] = []
    errors: list[str] = []

    if not agents_path.exists():
        errors.append(f"Missing Agent authoritative mapping document: {agents_path}")
        return {}, warnings, errors
    if not skills_path.exists():
        errors.append(f"Missing Skill list document: {skills_path}")
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
                errors.append(f"Agent mapping refers to a non-existent Skill file: {skill}")

    for item in shared_rules:
        skill = item["skill"]
        if skill not in skill_catalog_set:
            warnings.append(f"Shared Skill arbitration rule refers to a non-persisted Skill: {skill}")
        for agent in item["agents"]:
            skill_owners.setdefault(skill, set()).add(agent)

    for skill in skill_catalog:
        if skill not in skill_owners:
            warnings.append(f"Skill is not bound to a responsible Agent: {skill}")

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
    """Write the unified dispatch rules JSON file."""
    payload, warnings, errors = build_agent_dispatch_payload(specs_dir)
    target = specs_dir / "meta/index/agent-dispatch.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target, warnings, errors


def _matching_stage_score(stage_query: str, stage_text: str) -> int:
    """Calculate the matching score between input stage and Agent's responsible stage text."""
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
    """Normalize the skill list parameters passed from the command line."""
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
    """Resolve task dispatch suggestions based on unified mapping."""
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
            why.append(f"Stage match +{stage_score}")

        for skill in row.get("skills", []):
            if skill in skill_hints:
                score += 5
                why.append(f"Skill specified {skill} +5")
            skill_token = skill.removesuffix("-skill").replace("-", " ")
            if skill_token and skill_token in query:
                score += 2
                why.append(f"Task hit Skill keyword {skill} +2")

        if agent in query:
            score += 2
            why.append("Task explicitly mentions Agent +2")

        if score > 0:
            scores[agent] = score
            reasons[agent] = why

    for keyword, mapped_agent in KEYWORD_AGENT_MAP.items():
        if keyword in query and mapped_agent not in scores:
            scores[mapped_agent] = 3
            reasons[mapped_agent] = [f"Keyword match '{keyword}' → {mapped_agent} +3"]

    if not scores:
        primary_agent = fallback_agent
        primary_score = 0
        primary_reasons = ["No explicit rules hit, using default orchestrator dispatch"]
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
