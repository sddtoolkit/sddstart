"""
Validation and construction of command handler mappings.

## Specification References

| Specification Document | Reference ID | Applicable Section |
|------------------------|--------------|--------------------|
| Tool List and Format   | tool-adapters.json | Command Definition |
| Agent Collaboration Charter | G05     | Tool Adaptation    |

### tool-adapters.json Definition
- Command handler functions must correspond one-to-one with CLI subcommands.
- Missing handler functions must raise an error.

### G05-Agent Collaboration Charter Requirements
- Tool commands must be called through a unified entry point.
- Command handling must return standard exit codes.

## Command List

| Command | Function | Spec Source |
|---------|----------|-------------|
| initialize | Initialize specs directory | G01-Governance and Process |
| generate-index | Generate index files | S04-Quality Assurance |
| generate-traceability-matrix | Generate traceability matrix | S04-Traceability Integrity |
| generate-agent-dispatch | Generate dispatch rules | G05-Agent Collaboration |
| generate-tool-adapters | Generate tool adapters | tool-adapters.json |
| create-* | Create various documents | S01-Document Coding |
| check-* | Execute various checks | S04-Quality Assurance |
| locate-document | Locate document | S01-Reference ID |
| trace-dependencies | Trace dependencies | S06-Evidence Association |

See also:
- specs/meta/index/tool-adapters.json
- specs/govs/G05-Agent-Collaboration-Charter.md
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping

# Command handler function type alias
CommandHandler = Callable[[argparse.Namespace], int]

# Spec Ref: tool-adapters.json - Required command handler functions
REQUIRED_HANDLER_KEYS: tuple[str, ...] = (
    "initialize",
    "version",
    "generate-index",
    "generate-traceability-matrix",
    "generate-agent-dispatch",
    "generate-tool-adapters",
    "create-requirement",
    "create-design",
    "create-adr",
    "create-task",
    "create-test",
    "create-release",
    "check-status",
    "check-quality-gates",
    "validate-requirement",
    "validate-design",
    "check-changelog",
    "check-governance",
    "check-dependencies",
    "check-code-quality",
    "check-completeness",
    "check-naming",
    "check-document-coding",
    "bundle-task-context",
    "trace-code",
    "locate-document",
    "read-document",
    "trace-dependencies",
    "rename-document",
    "build-reference-index",
    "find-references-to",
    "find-references-from",
    "update-references",
    "delete-references",
    "check-orphaned-references",
    "reference-report",
    "check-drift",
    "resolve-agent-dispatch",
    "list-tool-adapters",
    "add-tool-adapter",
    "remove-tool-adapter",
)


def build_handler_map(handlers: Mapping[str, CommandHandler]) -> dict[str, CommandHandler]:
    """
    Validate and return the command handler function mapping.

    Spec Ref: tool-adapters.json - Command integrity check

    Args:
        handlers: Mapping of command names to handler functions

    Returns:
        dict[str, CommandHandler]: Validated handler function mapping

    Raises:
        KeyError: Missing required command handler function
    """
    missing = [key for key in REQUIRED_HANDLER_KEYS if key not in handlers]
    if missing:
        missing_text = ", ".join(missing)
        raise KeyError(f"Missing command handler function mapping: {missing_text}")
    return dict(handlers)
