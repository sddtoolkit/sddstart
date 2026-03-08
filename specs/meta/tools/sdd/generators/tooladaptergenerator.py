"""
多工具入口与适配清单管理。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 工具清单与格式 | tool-adapters.json | 全文 |
| Agent协作宪章 | G05 | 工具适配 |

### tool-adapters.json 定义
- 多工具入口文件的统一配置清单
- 定义工具与入口文件的映射关系
- 支持共享入口和专用入口

### G05-Agent协作宪章 要求
- 工具必须通过适配器配置接入
- 入口文件必须包含统一约束引用
- 调度契约必须指向 agent-dispatch.json

## 支持的入口格式

| 格式 | 说明 | 示例路径 |
|------|------|----------|
| markdown | Markdown 入口文件 | CLAUDE.md, AGENTS.md |
| text | 纯文本配置 | settings.txt |
| crush-init | Crush 工具引导文件 | .crush/init |

## 实现映射

| 函数 | 规范要求 | 规范章节 |
|------|----------|----------|
| `build_default_tool_adapter_manifest()` | 默认适配清单 | tool-adapters.json |
| `sync_tool_adapter_entries()` | 同步入口工件 | G05-工具适配 |
| `add_tool_adapter()` | 添加工具适配 | tool-adapters.json |

参见：
- specs/meta/index/tool-adapters.json
- specs/govs/G05-Agent协作宪章.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 规范引用：tool-adapters.json - 适配清单路径
MANIFEST_REL_PATH = "specs/meta/index/tool-adapters.json"

# 规范引用：tool-adapters.json - 支持的入口格式
SUPPORTED_ENTRY_FORMATS = {"markdown", "text", "crush-init"}


def _utc_now_iso() -> str:
    """返回 UTC ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _slugify_tool_id(raw: str) -> str:
    """将工具标识归一化为小写短横线 slug。"""
    text = raw.strip().lower().replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _making_entry_id(path: str, fmt: str) -> str:
    """根据路径和格式生成稳定入口 ID。"""
    slug = _slugify_tool_id(path.replace("/", "-").replace(".", "-"))
    return f"entry-{slug}-{fmt}"


def build_default_tool_adapter_manifest() -> dict[str, Any]:
    """构建默认适配清单。"""
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
    """返回工具适配清单绝对路径。"""
    return repo_root / MANIFEST_REL_PATH


def load_tool_adapter_manifest(repo_root: Path) -> dict[str, Any]:
    """读取适配清单；缺失时返回默认清单。"""
    path = _manifest_path(repo_root)
    if not path.exists():
        return build_default_tool_adapter_manifest()
    return json.loads(path.read_text(encoding="utf-8"))


def write_tool_adapter_manifest(repo_root: Path, manifest: dict[str, Any]) -> Path:
    """写入适配清单。"""
    path = _manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.setdefault("meta", {})
    manifest["meta"]["updated_at"] = _utc_now_iso()
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _resolve_repo_path(repo_root: Path, rel_path: str) -> Path:
    """将相对路径解析为仓库内安全路径。"""
    if Path(rel_path).is_absolute():
        raise ValueError(f"拒绝绝对路径：{rel_path}")
    target = (repo_root / rel_path).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"路径越界：{rel_path}") from exc
    return target


def _entry_content_markdown(path: str, tool_names: list[str]) -> str:
    """生成 Markdown 入口文件内容。"""
    title = Path(path).name
    tools_text = "、".join(tool_names) if tool_names else "（未绑定工具）"
    return "\n".join(
        [
            f"# {title}",
            "",
            f"本入口文件服务工具：{tools_text}",
            "",
            "## 统一约束",
            "- Agent 权威映射：`specs/meta/agents/agents.md`",
            "- Skill 权威清单：`specs/meta/skills/skills.md`",
            "- 调度契约：`specs/meta/index/agent-dispatch.json`",
            "- 工具清单与格式：`specs/meta/index/tool-adapters.json`",
            "",
            "## 执行顺序",
            "1. `python3 specs/meta/tools/sddtool.py generate-agent-dispatch`",
            "2. `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<任务描述>\" --json`",
            "3. 按输出的 `primary_agent` 与 `recommended_skills` 执行。",
            "",
            "## 常用命令",
            "- `python3 specs/meta/tools/sddtool.py initialize`",
            "- `python3 specs/meta/tools/sddtool.py generate-index`",
            "- `python3 specs/meta/tools/sddtool.py generate-traceability-matrix`",
            "- `python3 specs/meta/tools/sddtool.py check-status`",
            "- `python3 specs/meta/tools/sddtool.py check-governance`",
            "- `python3 specs/meta/tools/sddtool.py check-completeness`",
            "- `python3 specs/meta/tools/sddtool.py check-naming`",
            "- `python3 specs/meta/tools/sddtool.py check-drift`",
            "",
            "_该文件由 `generate-tool-adapters` 自动生成。_",
            "",
        ]
    )


def _entry_content_text(path: str, tool_names: list[str]) -> str:
    """生成纯文本入口文件内容。"""
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
    """生成 `.crush/init` 引导内容。"""
    return "\n".join(
        [
            "入口文件：`CRUSH.md`",
            "",
            "执行约束：",
            "1. 先读取 `specs/meta/agents/agents.md` 与 `specs/meta/skills/skills.md`。",
            "2. 先执行 `python3 specs/meta/tools/sddtool.py generate-agent-dispatch` 更新统一调度规则。",
            "3. 接收任务后执行 `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task \"<任务描述>\" --json`。",
            "4. 按输出中的 `primary_agent` 与 `recommended_skills` 调度执行，冲突按 `shared_skill_arbitration` 处理。",
            "",
            "# generated-by: generate-tool-adapters",
            "",
        ]
    )


def sync_tool_adapter_entries(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    """按清单写入入口工件。"""
    tools_by_id = {tool.get("tool_id"): tool for tool in manifest.get("tools", []) if tool.get("enabled", True)}
    written: list[str] = []

    for entry in manifest.get("entries", []):
        fmt = entry.get("format", "")
        if fmt not in SUPPORTED_ENTRY_FORMATS:
            raise ValueError(f"不支持的入口格式：{fmt}")

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
    """返回扁平化工具适配清单视图。"""
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
    """确保工具 ID 不重复。"""
    if any(item.get("tool_id") == tool_id for item in manifest.get("tools", [])):
        raise ValueError(f"工具已存在：{tool_id}")


def _get_or_create_entry(
    manifest: dict[str, Any],
    path: str,
    fmt: str,
    shared: bool,
) -> str:
    """获取已存在入口定义，或按参数创建新入口定义。"""
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
    """向清单添加工具适配定义。"""
    normalized_tool_id = _slugify_tool_id(tool_id)
    if not normalized_tool_id:
        raise ValueError("tool_id 不能为空")
    if entry_format not in SUPPORTED_ENTRY_FORMATS:
        raise ValueError(f"不支持的入口格式：{entry_format}")
    _require_tool_not_exists(manifest, normalized_tool_id)

    entry_ids: list[str] = []
    primary_entry_id = _get_or_create_entry(manifest, entry_file, entry_format, shared_entry)
    entry_ids.append(primary_entry_id)

    for path, fmt in extra_entries or []:
        if fmt not in SUPPORTED_ENTRY_FORMATS:
            raise ValueError(f"不支持的扩展入口格式：{fmt}")
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
    """从清单移除工具，并返回应清理的空入口文件路径。"""
    normalized_tool_id = _slugify_tool_id(tool_id)
    tools = manifest.get("tools", [])

    target = next((item for item in tools if item.get("tool_id") == normalized_tool_id), None)
    if target is None:
        raise ValueError(f"工具不存在：{normalized_tool_id}")

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
    """删除已无工具引用的入口文件。"""
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
