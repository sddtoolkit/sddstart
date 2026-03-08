"""
Multi-tool entry and adapter manifest management.

## Specification Reference

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Tool Manifest and Format | tool-adapters.json | Entire document |
| Agent Collaboration Charter | G05 | Tool Adaptation |

### tool-adapters.json Definition
- Unified configuration manifest for multi-tool entry files
- Defines mapping between tools and entry files
- Supports shared and dedicated entries

### G05-Agent Collaboration Charter Requirements
- Tools must be integrated via adapter configuration
- Entry files must contain unified constraint references
- Dispatch contract must point to agent-dispatch.json

## Supported Entry Formats

| Format | Description | Example Path |
|------|----------|----------|
| markdown | Markdown entry file | CLAUDE.md, AGENTS.md |
| text | Plain text configuration | settings.txt |
| crush-init | Crush tool bootstrap file | .crush/init |

## Implementation Mapping

| Function | Specification Requirement | Specification Section |
|------|----------|----------|
| `build_default_tool_adapter_manifest()` | Default adapter manifest | tool-adapters.json |
| `sync_tool_adapter_entries()` | Sync entry artifacts | G05-Tool Adaptation |
| `add_tool_adapter()` | Add tool adaptation | tool-adapters.json |

See:
- specs/meta/index/tool-adapters.json
- specs/govs/G05-Agent Collaboration Charter.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Specification Reference: tool-adapters.json - Adapter manifest path
MANIFEST_REL_PATH = "specs/meta/index/tool-adapters.json"

# Specification Reference: tool-adapters.json - Supported entry formats
SUPPORTED_ENTRY_FORMATS = {"markdown", "text", "crush-init"}


def _utc_now_iso() -> str:
    """Return UTC ISO8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _slugify_tool_id(raw: str) -> str:
    """Normalize tool identifier to lowercase hyphenated slug."""
    text = raw.strip().lower().replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _making_entry_id(path: str, fmt: str) -> str:
    """Generate a stable entry ID based on path and format."""
    slug = _slugify_tool_id(path.replace("/", "-").replace(".", "-"))
    return f"entry-{slug}-{fmt}"


def build_default_tool_adapter_manifest() -> dict[str, Any]:
    """Build the default adapter manifest."""
    entries = [
        {
            "entry_id": "entry-agents-md",
            "path": "AGENTS.md",
            "format": "markdown",
            "shared": True,
            "tools": ["codex", "kiro", "kimi-code", "opencode"],
        },
        {
            "entry_id": "entry-claude-md",
            "path": "CLAUDE.md",
            "format": "markdown",
            "shared": False,
            "tools": ["claude-code"],
        },
        {
            "entry_id": "entry-gemini-md",
            "path": "GEMINI.md",
            "format": "markdown",
            "shared": False,
            "tools": ["gemini-cli"],
        },
        {
            "entry_id": "entry-crush-md",
            "path": "CRUSH.md",
            "format": "markdown",
            "shared": False,
            "tools": ["crush"],
        },
        {
            "entry_id": "entry-crush-init",
            "path": ".crush/init",
            "format": "crush-init",
            "shared": False,
            "tools": ["crush"],
        },
    ]

    tools = [
        {
            "tool_id": "codex",
            "display_name": "Codex",
            "enabled": True,
            "entry_ids": ["entry-agents-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "kiro",
            "display_name": "Kiro",
            "enabled": True,
            "entry_ids": ["entry-agents-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "shared-markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "claude-code",
            "display_name": "Claude Code",
            "enabled": True,
            "entry_ids": ["entry-claude-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "gemini-cli",
            "display_name": "Gemini CLI",
            "enabled": True,
            "entry_ids": ["entry-gemini-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "kimi-code",
            "display_name": "Kimi Code",
            "enabled": True,
            "entry_ids": ["entry-agents-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "shared-markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "crush",
            "display_name": "Crush",
            "enabled": True,
            "entry_ids": ["entry-crush-md", "entry-crush-init"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "markdown-entry + init-script + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
        {
            "tool_id": "opencode",
            "display_name": "OpenCode",
            "enabled": True,
            "entry_ids": ["entry-agents-md"],
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": "shared-markdown-entry + dispatch-json",
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        },
    ]

    return {
        "meta": {
            "schema": "sdd.tool-adapters.v1",
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        },
        "entries": entries,
        "tools": tools,
    }


def _manifest_path(repo_root: Path) -> Path:
    """Return the absolute path to the tool adapter manifest."""
    return repo_root / MANIFEST_REL_PATH


def load_tool_adapter_manifest(repo_root: Path) -> dict[str, Any]:
    """Load the adapter manifest; return default manifest if missing."""
    path = _manifest_path(repo_root)
    if not path.exists():
        return build_default_tool_adapter_manifest()
    return json.loads(path.read_text(encoding="utf-8"))


def write_tool_adapter_manifest(repo_root: Path, manifest: dict[str, Any]) -> Path:
    """Write the adapter manifest."""
    path = _manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.setdefault("meta", {})
    manifest["meta"]["updated_at"] = _utc_now_iso()
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _resolve_repo_path(repo_root: Path, rel_path: str) -> Path:
    """Resolve a relative path to a safe path within the repository."""
    if Path(rel_path).is_absolute():
        raise ValueError(f"Absolute path rejected: {rel_path}")
    target = (repo_root / rel_path).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path out of bounds: {rel_path}") from exc
    return target


def _entry_content_markdown(path: str, tool_names: list[str]) -> str:
    """Generate Markdown entry file content."""
    title = Path(path).name
    tools_text = ", ".join(tool_names) if tool_names else "(No tools bound)"
    return "\n".join(
        [
            f"# {title}",
            "",
            f"This entry file serves the following tools: {tools_text}",
            "",
            "## Unified Constraints",
            "- Agent Authoritative Mapping: `specs/meta/agents/agents.md`",
            "- Skill Authoritative List: `specs/meta/skills/skills.md`",
            "- Dispatch Contract: `specs/meta/index/agent-dispatch.json`",
            "- Tool Manifest and Format: `specs/meta/index/tool-adapters.json`",
            "",
            "## Execution Order",
            "1. `python3 specs/meta/tools/sddtool.py generate-agent-dispatch`",
            "2. `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task_description>\" --json`",
            "3. Execute according to the output `primary_agent` and `recommended_skills`.",
            "",
            "## Common Commands",
            "- `python3 specs/meta/tools/sddtool.py initialize`",
            "- `python3 specs/meta/tools/sddtool.py generate-index`",
            "- `python3 specs/meta/tools/sddtool.py generate-traceability-matrix`",
            "- `python3 specs/meta/tools/sddtool.py check-status`",
            "- `python3 specs/meta/tools/sddtool.py check-governance`",
            "- `python3 specs/meta/tools/sddtool.py check-completeness`",
            "- `python3 specs/meta/tools/sddtool.py check-naming`",
            "- `python3 specs/meta/tools/sddtool.py check-drift`",
            "",
            "_This file was automatically generated by `generate-tool-adapters`._",
            "",
        ]
    )


def _entry_content_text(path: str, tool_names: list[str]) -> str:
    """Generate plain text entry file content."""
    tools_text = ", ".join(tool_names)
    return (
        f"entry={path}\n"
        f"tools={tools_text}\n"
        "agent_definition=specs/meta/agents/agents.md\n"
        "skill_definition=specs/meta/skills/skills.md\n"
        "dispatch_contract=specs/meta/index/agent-dispatch.json\n"
        "resolver=python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json\n"
    )


def _entry_content_crush_init() -> str:
    """Generate .crush/init bootstrap content."""
    return "\n".join(
        [
            "Entry file: `CRUSH.md`",
            "",
            "Execution constraints:",
            "1. First read `specs/meta/agents/agents.md` and `specs/meta/skills/skills.md`.",
            "2. Execute `python3 specs/meta/tools/sddtool.py generate-agent-dispatch` to update unified dispatch rules.",
            "3. Execute `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task_description>\" --json` after receiving task.",
            "4. Dispatch and execute according to the output `primary_agent` and `recommended_skills`; handle conflicts per `shared_skill_arbitration`.",
            "",
            "# generated-by: generate-tool-adapters",
            "",
        ]
    )


def sync_tool_adapter_entries(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    """Write entry artifacts according to the manifest."""
    tools_by_id = {tool.get("tool_id"): tool for tool in manifest.get("tools", []) if tool.get("enabled", True)}
    written: list[str] = []

    for entry in manifest.get("entries", []):
        fmt = entry.get("format", "")
        if fmt not in SUPPORTED_ENTRY_FORMATS:
            raise ValueError(f"Unsupported entry format: {fmt}")

        tool_ids = [tool_id for tool_id in entry.get("tools", []) if tool_id in tools_by_id]
        if not tool_ids:
            continue
        tool_names = [tools_by_id[tool_id].get("display_name", tool_id) for tool_id in tool_ids]

        path_text = entry.get("path", "")
        target = _resolve_repo_path(repo_root, path_text)
        target.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "markdown":
            content = _entry_content_markdown(path_text, tool_names)
        elif fmt == "text":
            content = _entry_content_text(path_text, tool_names)
        else:
            content = _entry_content_crush_init()
        target.write_text(content, encoding="utf-8")
        written.append(path_text)
    return written


def list_tool_adapters(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Return a flattened view of the tool adapter manifest."""
    entries_by_id = {entry.get("entry_id"): entry for entry in manifest.get("entries", [])}
    rows: list[dict[str, str]] = []
    for tool in manifest.get("tools", []):
        tool_id = str(tool.get("tool_id", ""))
        display_name = str(tool.get("display_name", tool_id))
        enabled = "yes" if tool.get("enabled", True) else "no"
        entry_ids = tool.get("entry_ids", [])
        entry_desc: list[str] = []
        for entry_id in entry_ids:
            entry = entries_by_id.get(entry_id, {})
            path = entry.get("path", f"<missing:{entry_id}>")
            fmt = entry.get("format", "?")
            mode = "shared" if entry.get("shared") else "dedicated"
            entry_desc.append(f"{path}({fmt},{mode})")
        rows.append(
            {
                "tool_id": tool_id,
                "display_name": display_name,
                "enabled": enabled,
                "definition_format": str(tool.get("definition_format", "")),
                "entries": "; ".join(entry_desc),
            }
        )
    return rows


def _require_tool_not_exists(manifest: dict[str, Any], tool_id: str) -> None:
    """Ensure tool ID is not duplicated."""
    if any(item.get("tool_id") == tool_id for item in manifest.get("tools", [])):
        raise ValueError(f"Tool already exists: {tool_id}")


def _get_or_create_entry(
    manifest: dict[str, Any],
    path: str,
    fmt: str,
    shared: bool,
) -> str:
    """Get an existing entry definition or create a new one based on parameters."""
    entries = manifest.setdefault("entries", [])
    if shared:
        for entry in entries:
            if entry.get("path") == path and entry.get("format") == fmt:
                entry["shared"] = True
                return entry["entry_id"]

    entry_id = _making_entry_id(path, fmt)
    suffix = 1
    existing_ids = {entry.get("entry_id") for entry in entries}
    base = entry_id
    while entry_id in existing_ids:
        suffix += 1
        entry_id = f"{base}-{suffix}"

    entries.append(
        {
            "entry_id": entry_id,
            "path": path,
            "format": fmt,
            "shared": bool(shared),
            "tools": [],
        }
    )
    return entry_id


def add_tool_adapter(
    manifest: dict[str, Any],
    tool_id: str,
    display_name: str,
    entry_file: str,
    entry_format: str,
    shared_entry: bool,
    extra_entries: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Add a tool adaptation definition to the manifest."""
    normalized_tool_id = _slugify_tool_id(tool_id)
    if not normalized_tool_id:
        raise ValueError("tool_id cannot be empty")
    if entry_format not in SUPPORTED_ENTRY_FORMATS:
        raise ValueError(f"Unsupported entry format: {entry_format}")
    _require_tool_not_exists(manifest, normalized_tool_id)

    entry_ids: list[str] = []
    primary_entry_id = _get_or_create_entry(manifest, entry_file, entry_format, shared_entry)
    entry_ids.append(primary_entry_id)

    for path, fmt in extra_entries or []:
        if fmt not in SUPPORTED_ENTRY_FORMATS:
            raise ValueError(f"Unsupported extra entry format: {fmt}")
        entry_ids.append(_get_or_create_entry(manifest, path, fmt, False))

    tools = manifest.setdefault("tools", [])
    if entry_format == "markdown":
        if shared_entry:
            definition_format = "shared-markdown-entry + dispatch-json"
        else:
            definition_format = "markdown-entry + dispatch-json"
    else:
        definition_format = "adapter-entry + dispatch-json"
    tools.append(
        {
            "tool_id": normalized_tool_id,
            "display_name": display_name or normalized_tool_id,
            "enabled": True,
            "entry_ids": entry_ids,
            "agent_definition": "specs/meta/agents/agents.md",
            "skill_definition": "specs/meta/skills/skills.md",
            "definition_format": definition_format,
            "dispatch_contract": "specs/meta/index/agent-dispatch.json",
            "dispatch_resolver": "python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<task>\" --json",
        }
    )

    for entry in manifest.get("entries", []):
        if entry.get("entry_id") in entry_ids:
            tool_ids = set(entry.get("tools", []))
            tool_ids.add(normalized_tool_id)
            entry["tools"] = sorted(tool_ids)

    return manifest


def remove_tool_adapter(manifest: dict[str, Any], tool_id: str) -> tuple[dict[str, Any], list[str]]:
    """Remove a tool from the manifest and return paths of empty entry files to be cleaned up."""
    normalized_tool_id = _slugify_tool_id(tool_id)
    tools = manifest.get("tools", [])

    target = next((item for item in tools if item.get("tool_id") == normalized_tool_id), None)
    if target is None:
        raise ValueError(f"Tool does not exist: {normalized_tool_id}")

    entry_ids = set(target.get("entry_ids", []))
    manifest["tools"] = [item for item in tools if item.get("tool_id") != normalized_tool_id]

    removed_entry_paths: list[str] = []
    kept_entries: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if entry.get("entry_id") in entry_ids:
            tool_ids = [item for item in entry.get("tools", []) if item != normalized_tool_id]
            entry["tools"] = tool_ids
            if not tool_ids:
                removed_entry_paths.append(str(entry.get("path", "")))
                continue
        kept_entries.append(entry)
    manifest["entries"] = kept_entries
    return manifest, removed_entry_paths


def delete_entry_files(repo_root: Path, paths: list[str]) -> list[str]:
    """Delete entry files that are no longer referenced by any tools."""
    deleted: list[str] = []
    for rel_path in paths:
        if not rel_path:
            continue
        target = _resolve_repo_path(repo_root, rel_path)
        if target.exists():
            target.unlink()
            deleted.append(rel_path)
    return deleted


__all__ = [
    "MANIFEST_REL_PATH",
    "SUPPORTED_ENTRY_FORMATS",
    "add_tool_adapter",
    "build_default_tool_adapter_manifest",
    "delete_entry_files",
    "list_tool_adapters",
    "load_tool_adapter_manifest",
    "remove_tool_adapter",
    "sync_tool_adapter_entries",
    "write_tool_adapter_manifest",
]
