"""SDD 生成器子包。"""

from .agentdispatchgenerator import (
    build_agent_dispatch_payload,
    parse_agent_skill_rows,
    parse_shared_skill_rules,
    resolve_agent_dispatch,
    write_agent_dispatch_file,
)
from .tooladaptergenerator import (
    MANIFEST_REL_PATH,
    SUPPORTED_ENTRY_FORMATS,
    add_tool_adapter,
    build_default_tool_adapter_manifest,
    delete_entry_files,
    list_tool_adapters,
    load_tool_adapter_manifest,
    remove_tool_adapter,
    sync_tool_adapter_entries,
    write_tool_adapter_manifest,
)

__all__ = [
    "build_agent_dispatch_payload",
    "build_default_tool_adapter_manifest",
    "MANIFEST_REL_PATH",
    "parse_agent_skill_rows",
    "parse_shared_skill_rules",
    "resolve_agent_dispatch",
    "SUPPORTED_ENTRY_FORMATS",
    "add_tool_adapter",
    "delete_entry_files",
    "list_tool_adapters",
    "load_tool_adapter_manifest",
    "remove_tool_adapter",
    "sync_tool_adapter_entries",
    "write_agent_dispatch_file",
    "write_tool_adapter_manifest",
]
