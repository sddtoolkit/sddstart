"""
CLI subcommand registry.

## Specification References
This module defines all CLI subcommands for sddtool.py.
Mapping to CLI commands:

| Command Category | Corresponding Checker/Generator |
|------------------|---------------------------------|
| check-*          | Corresponding to checkers/*checker.py |
| create-*         | Corresponding to document template creation |
| generate-*       | Corresponding to generators/*.py |
| locate/read/trace| Document localization and tracing |
| reference-*      | Reference relationship management |

## Command Groups

### Initialization and Generation
- initialize: Initialize the specs directory
- generate-index: Generate the index
- generate-traceability-matrix: Generate the traceability matrix
- generate-agent-dispatch: Generate dispatch rules
- generate-tool-adapters: Generate tool adapters

### Document Creation
- create-requirement: Create a requirement document
- create-design: Create a design document
- create-adr: Create an ADR document
- create-task: Create a task document
- create-test: Create a test document
- create-release: Create a release document

### Specification Checks
- check-status: Check completeness
- check-naming: Check naming conventions
- check-document-coding: Check document coding
- check-completeness: Check traceability completeness
- check-governance: Check governance approval
- check-dependencies: Check dependency risk
- check-code-quality: Check code quality
- check-drift: Check specification drift
- validate-requirement: Validate a requirement document
- validate-design: Validate a design document
- check-changelog: Check the changelog

### Document Operations
- locate-document: Locate a document
- read-document: Read a document
- trace-dependencies: Trace dependencies
- rename-document: Rename a document

### Reference Management
- build-reference-index: Build the reference index
- find-references-to: Query reference targets
- find-references-from: Query reference sources
- update-references: Update references
- delete-references: Delete references
- check-orphaned-references: Check for orphaned references
- reference-report: Generate a reference report

### Dispatch and Tools
- resolve-agent-dispatch: Resolve dispatch recommendations
- list-tool-adapters: List tool adapters
- add-tool-adapter: Add a tool adapter
- remove-tool-adapter: Remove a tool adapter
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from sdd.generators.tooladaptergenerator import SUPPORTED_ENTRY_FORMATS

# Definition of command handler function type
CommandHandler = Callable[[argparse.Namespace], int]


def _requiring_handler(handlers: dict[str, CommandHandler], key: str) -> CommandHandler:
    """
    Read and validate the command handler function mapping.

    Args:
        handlers: Command handler function mapping.
        key: Command key name.

    Returns:
        CommandHandler: Corresponding handler function.

    Raises:
        KeyError: Missing required handler function.
    """
    try:
        return handlers[key]
    except KeyError as exc:
        raise KeyError(f"Missing command handler function: {key}") from exc


def register_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, CommandHandler]) -> None:
    """Register all CLI subcommands with the parser."""
    version_cmd = subparsers.add_parser("version", help="Show SDD system and tool version number")
    version_cmd.set_defaults(running=_requiring_handler(handlers, "version"))

    init_cmd = subparsers.add_parser("initialize", help="Initialize or complete the specs directory")
    init_cmd.set_defaults(running=_requiring_handler(handlers, "initialize"))

    gen_cmd = subparsers.add_parser("generate-index", help="Generate specs index")
    gen_cmd.set_defaults(running=_requiring_handler(handlers, "generate-index"))

    trace_cmd = subparsers.add_parser(
        "generate-traceability-matrix",
        help="Generate traceability matrix (md/json)",
    )
    trace_cmd.set_defaults(running=_requiring_handler(handlers, "generate-traceability-matrix"))

    agent_dispatch_cmd = subparsers.add_parser(
        "generate-agent-dispatch",
        help="Generate unified Agent/Skill dispatch rules",
    )
    agent_dispatch_cmd.set_defaults(running=_requiring_handler(handlers, "generate-agent-dispatch"))

    tool_adapters_cmd = subparsers.add_parser(
        "generate-tool-adapters",
        help="Generate/synchronize multi-tool entry and adapter manifest",
    )
    tool_adapters_cmd.set_defaults(running=_requiring_handler(handlers, "generate-tool-adapters"))

    req_cmd = subparsers.add_parser("create-requirement", help="Create requirement document")
    req_cmd.add_argument("slug", nargs="?", help="Short description of the requirement (SLUG)")
    req_cmd.add_argument("--ccc", help="3-digit classification code (default inferred from project intro)")
    req_cmd.add_argument("--nn", help="2-digit sequence code (default auto-incremented)")
    req_cmd.add_argument("--intro", help="Project introduction, used to infer CCC code")
    req_cmd.set_defaults(running=_requiring_handler(handlers, "create-requirement"))

    design_cmd = subparsers.add_parser("create-design", help="Create design document")
    design_cmd.add_argument("slug", nargs="?", help="Short description of the design (SLUG)")
    design_cmd.add_argument("--ccc", help="3-digit classification code (default inferred from project intro)")
    design_cmd.add_argument("--nn", help="2-digit sequence code (default auto-incremented)")
    design_cmd.add_argument("--intro", help="Project introduction, used to infer CCC code")
    design_cmd.set_defaults(running=_requiring_handler(handlers, "create-design"))

    adr_cmd = subparsers.add_parser("create-adr", help="Create ADR")
    adr_cmd.add_argument("slug", help="Short description of the decision (SLUG)")
    adr_cmd.add_argument("--ccc", help="3-digit classification code (default inferred from project intro)")
    adr_cmd.add_argument("--nn", help="2-digit sequence code (default auto-incremented)")
    adr_cmd.add_argument("--intro", help="Project introduction, used to infer CCC code")
    adr_cmd.set_defaults(running=_requiring_handler(handlers, "create-adr"))

    task_cmd = subparsers.add_parser("create-task", help="Create task document")
    task_cmd.add_argument("slug", help="Short description of the task (SLUG)")
    task_cmd.add_argument("--ccc", help="3-digit classification code (default inferred from project intro)")
    task_cmd.add_argument("--nn", help="2-digit sequence code (default auto-incremented)")
    task_cmd.add_argument("--intro", help="Project introduction, used to infer CCC code")
    task_cmd.set_defaults(running=_requiring_handler(handlers, "create-task"))

    test_cmd = subparsers.add_parser("create-test", help="Create test document")
    test_cmd.add_argument("scope", help="Scope")
    test_cmd.add_argument("test_id", help="Test ID")
    test_cmd.set_defaults(running=_requiring_handler(handlers, "create-test"))

    release_cmd = subparsers.add_parser("create-release", help="Create release document")
    release_cmd.add_argument("version", help="Version number")
    release_cmd.set_defaults(running=_requiring_handler(handlers, "create-release"))

    status_cmd = subparsers.add_parser("check-status", help="Check spec completeness")
    status_cmd.set_defaults(running=_requiring_handler(handlers, "check-status"))

    gates_cmd = subparsers.add_parser("check-quality-gates", help="Perform full quality gate check (naming/drift/completeness)")
    gates_cmd.set_defaults(running=_requiring_handler(handlers, "check-quality-gates"))

    req_val_cmd = subparsers.add_parser(
        "validate-requirement",
        help="Check requirement document",
    )
    req_val_cmd.set_defaults(running=_requiring_handler(handlers, "validate-requirement"))

    design_val_cmd = subparsers.add_parser("validate-design", help="Check design document")
    design_val_cmd.set_defaults(running=_requiring_handler(handlers, "validate-design"))

    changelog_cmd = subparsers.add_parser("check-changelog", help="Check the changelog")
    changelog_cmd.set_defaults(running=_requiring_handler(handlers, "check-changelog"))

    governance_cmd = subparsers.add_parser(
        "check-governance",
        help="Check governance approval chain fields",
    )
    governance_cmd.set_defaults(running=_requiring_handler(handlers, "check-governance"))

    dep_cmd = subparsers.add_parser(
        "check-dependencies",
        help="Check dependency risk and reproducibility",
    )
    dep_cmd.set_defaults(running=_requiring_handler(handlers, "check-dependencies"))

    quality_cmd = subparsers.add_parser(
        "check-code-quality",
        help="Check code static quality signals",
    )
    quality_cmd.set_defaults(running=_requiring_handler(handlers, "check-code-quality"))

    complete_cmd = subparsers.add_parser(
        "check-completeness",
        help="Check requirement-to-test chain completeness",
    )
    complete_cmd.set_defaults(running=_requiring_handler(handlers, "check-completeness"))

    naming_cmd = subparsers.add_parser("check-naming", help="Check naming and index registration")
    naming_cmd.set_defaults(running=_requiring_handler(handlers, "check-naming"))

    # Context bundling command
    bundle_cmd = subparsers.add_parser("bundle-task-context", help="Aggregate REQ/DSN/ADR context associated with the task to tmp/")
    bundle_cmd.add_argument("task_id", help="Task ID, e.g., TK-101260901")
    bundle_cmd.set_defaults(running=_requiring_handler(handlers, "bundle-task-context"))

    trace_code_cmd = subparsers.add_parser("trace-code", help="Reverse trace specification sources from code files")
    trace_code_cmd.add_argument("file_path", help="Code file path")
    trace_code_cmd.set_defaults(running=_requiring_handler(handlers, "trace-code"))

    doc_coding_cmd = subparsers.add_parser(
        "check-document-coding",
        help="Check document coding standards (CCC-NN-YYWW system)",
    )
    doc_coding_cmd.set_defaults(running=_requiring_handler(handlers, "check-document-coding"))

    locate_doc_cmd = subparsers.add_parser(
        "locate-document",
        help="Locate document path based on document reference ID",
    )
    locate_doc_cmd.add_argument("ref_id", help="Document ID, e.g., RQ-10102, G01, S01")
    locate_doc_cmd.set_defaults(running=_requiring_handler(handlers, "locate-document"))

    read_doc_cmd = subparsers.add_parser(
        "read-document",
        help="Read document content based on document reference ID",
    )
    read_doc_cmd.add_argument("ref_id", help="Document ID, e.g., RQ-10102, G01, S01")
    read_doc_cmd.set_defaults(running=_requiring_handler(handlers, "read-document"))

    trace_deps_cmd = subparsers.add_parser(
        "trace-dependencies",
        help="Trace document dependencies (associated requirements, designs, tasks, code)",
    )
    trace_deps_cmd.add_argument("ref_id", help="Document ID, e.g., RQ-10102, DS-20101")
    trace_deps_cmd.add_argument("--json", action="store_true", dest="as_json", help="Output in JSON format")
    trace_deps_cmd.set_defaults(running=_requiring_handler(handlers, "trace-dependencies"))

    rename_doc_cmd = subparsers.add_parser(
        "rename-document",
        help="Rename document or change document reference ID",
    )
    rename_doc_cmd.add_argument(
        "old_identifier",
        help="Old filename (full) or document ID (e.g., RQ-10102). Use --by-ref-id when providing document ID",
    )
    rename_doc_cmd.add_argument("new_filename", help="New filename (full, e.g., RQ-10103-用户注册需求.md)")
    rename_doc_cmd.add_argument(
        "--by-ref-id",
        action="store_true",
        help="Interpret old_identifier as a document ID rather than a filename",
    )
    rename_doc_cmd.set_defaults(running=_requiring_handler(handlers, "rename-document"))

    drift_cmd = subparsers.add_parser("check-drift", help="Check implementation and specification source markers")
    drift_cmd.set_defaults(running=_requiring_handler(handlers, "check-drift"))

    list_tool_adapters_cmd = subparsers.add_parser(
        "list-tool-adapters",
        help="List tool adapter manifest",
    )
    list_tool_adapters_cmd.set_defaults(running=_requiring_handler(handlers, "list-tool-adapters"))

    add_tool_adapter_cmd = subparsers.add_parser(
        "add-tool-adapter",
        help="Add new tool adapter definition",
    )
    add_tool_adapter_cmd.add_argument("tool_id", help="Tool ID (e.g., opencode)")
    add_tool_adapter_cmd.add_argument("display_name", help="Tool display name")
    add_tool_adapter_cmd.add_argument("--entry-file", required=True, help="Entry file path (relative to repo root)")
    add_tool_adapter_cmd.add_argument(
        "--entry-format",
        default="markdown",
        choices=sorted(SUPPORTED_ENTRY_FORMATS),
        help="Entry file format",
    )
    add_tool_adapter_cmd.add_argument("--shared-entry", action="store_true", help="Whether the entry file is shared")
    add_tool_adapter_cmd.add_argument(
        "--extra-entry",
        action="append",
        help="Additional entries, format path:format, repeatable",
    )
    add_tool_adapter_cmd.set_defaults(running=_requiring_handler(handlers, "add-tool-adapter"))

    remove_tool_adapter_cmd = subparsers.add_parser(
        "remove-tool-adapter",
        help="Remove tool adapter definition and recycle empty entry files as needed",
    )
    remove_tool_adapter_cmd.add_argument("tool_id", help="Tool ID")
    remove_tool_adapter_cmd.set_defaults(running=_requiring_handler(handlers, "remove-tool-adapter"))

    resolve_dispatch_cmd = subparsers.add_parser(
        "resolve-agent-dispatch",
        help="Resolve task dispatch recommendations based on Agent/Skill definitions",
    )
    resolve_dispatch_cmd.add_argument("--task", required=True, help="Task description")
    resolve_dispatch_cmd.add_argument("--stage", help="Stage (optional)")
    resolve_dispatch_cmd.add_argument("--skills", action="append", help="Specify Skill (repeatable)")
    resolve_dispatch_cmd.add_argument("--json", action="store_true", dest="as_json", help="Output results as JSON")
    resolve_dispatch_cmd.set_defaults(running=_requiring_handler(handlers, "resolve-agent-dispatch"))

    # Reference management commands
    ref_build_cmd = subparsers.add_parser(
        "build-reference-index",
        help="Build document reference relationship index",
    )
    ref_build_cmd.set_defaults(running=_requiring_handler(handlers, "build-reference-index"))

    ref_find_to_cmd = subparsers.add_parser(
        "find-references-to",
        help="Query which documents reference a specified ID",
    )
    ref_find_to_cmd.add_argument("ref_id", help="Document ID, e.g., G01, S01, RQ-10102")
    ref_find_to_cmd.set_defaults(running=_requiring_handler(handlers, "find-references-to"))

    ref_find_from_cmd = subparsers.add_parser(
        "find-references-from",
        help="Query which documents are referenced by a specified document",
    )
    ref_find_from_cmd.add_argument("ref_id", help="Document ID")
    ref_find_from_cmd.set_defaults(running=_requiring_handler(handlers, "find-references-from"))

    ref_update_cmd = subparsers.add_parser(
        "update-references",
        help="Batch update reference relationships",
    )
    ref_update_cmd.add_argument("old_ref_id", help="Old reference ID")
    ref_update_cmd.add_argument("new_ref_id", help="New reference ID")
    ref_update_cmd.add_argument("--dry-run", action="store_true", help="Preview only, no actual modification")
    ref_update_cmd.set_defaults(running=_requiring_handler(handlers, "update-references"))

    ref_delete_cmd = subparsers.add_parser(
        "delete-references",
        help="Delete references to a specified document",
    )
    ref_delete_cmd.add_argument("ref_id", help="Document ID for which references should be deleted")
    ref_delete_cmd.add_argument("--dry-run", action="store_true", help="Preview only")
    ref_delete_cmd.set_defaults(running=_requiring_handler(handlers, "delete-references"))

    ref_orphaned_cmd = subparsers.add_parser(
        "check-orphaned-references",
        help="Check for orphaned references (referencing non-existent documents)",
    )
    ref_orphaned_cmd.set_defaults(running=_requiring_handler(handlers, "check-orphaned-references"))

    ref_report_cmd = subparsers.add_parser(
        "reference-report",
        help="Generate document reference relationship report",
    )
    ref_report_cmd.set_defaults(running=_requiring_handler(handlers, "reference-report"))
