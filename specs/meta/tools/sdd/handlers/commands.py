from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from collections.abc import Callable
from pathlib import Path

# --- Core Configuration & IO ---
from sdd.config import (
    BANNED_NAMES, CATEGORY_DIRECTORY_ROWS, DIRECTORIES, REPO_ROOT,
    REQUIRED_SPEC_FILES, SEED_CONTENTS, SPECIAL_MARKDOWN_NAMES,
    SPECS_DIR, SPEC_MARK, SUPPORTED_CODE_SUFFIXES, TEMPLATE_CONTENTS
)
from sdd.io import read_text_safe, check_file_integrity
from sdd.log import log_error, log_info, log_warning

# --- Common Utilities ---
from sdd.utils import (
    copy_template, get_current_date_slug, get_next_nn,
    get_yyww, normalize_id, normalize_md_token,
    read_first_heading, resolve_spec_path, validate_semver,
    validate_slug as validating_slug_value, write_file_safe,
    check_structured_bullets, count_specs_by_dir,
    ensure_gov_metadata, extract_registered_ids,
    list_files_depth_two, list_top_directories
)

# --- Checkers ---
from sdd.checkers.completenesschecker import check_completeness
from sdd.checkers.dependencychecker import check_dependencies
from sdd.checkers.documentcodingchecker import DocumentCodingChecker
from sdd.checkers.driftchecker import check_spec_drift as check_drift_files
from sdd.checkers.namingchecker import NamingChecker, is_ccc_coded
from sdd.checkers.qualitychecker import check_code_quality

# --- Generators ---
from sdd.generators.agentdispatchgenerator import (
    build_agent_dispatch_payload, resolve_agent_dispatch, write_agent_dispatch_file
)
from sdd.generators.changeloggenerator import check_changelog_file
from sdd.generators.dependencytracer import trace_dependencies
from sdd.generators.indexgenerator import write_index
from sdd.generators.tooladaptergenerator import (
    MANIFEST_REL_PATH, add_tool_adapter, delete_entry_files,
    list_tool_adapters, load_tool_adapter_manifest,
    remove_tool_adapter, sync_tool_adapter_entries,
    write_tool_adapter_manifest
)
from sdd.generators.traceabilitygenerator import generate_traceability_outputs

# --- Validators ---
from sdd.validators.designvalidator import check_design_file
from sdd.validators.reqvalidator import check_requirement_file
from sdd.validators.sectionvalidator import check_required_nonempty_bullets
from sdd.validators.speccompliance import check_required_files

from .commandhandlers import CommandHandler, build_handler_map

def refresh_index_after_change() -> int:
    """Refresh index registration after document changes."""
    # Keep index registration in sync with newly created spec files.
    return generate_index(argparse.Namespace())


def _create_from_template(template_rel: str, target_rel: str) -> int:
    """Reusable document creation flow: copy template and refresh index."""
    success = copy_template(template_rel, target_rel)
    if not success:
        return 1
    return refresh_index_after_change()


def _resolve_optional_slug_target(
    raw_name: str | None,
    field_name: str,
    default_target: str,
    named_target_builder: Callable[[str], str],
) -> str | None:
    """Resolve optional name parameter and generate target path."""
    if not raw_name:
        return default_target

    slug = validating_slug_value(raw_name, field_name)
    if slug is None:
        return None
    return named_target_builder(slug)


def _infer_ccc_from_text(text: str, prefix: str) -> str:
    """Infer CCC code based on text content."""
    text = text.lower()
    
    # Keyword mapping
    mapping = {
        "101": ["project", "outline", "governance", "specification", "charter", "architecture", "system", "process"],
        "201": ["frontend", "web", "react", "vue", "miniprogram", "app", "mobile", "interface", "ui"],
        "301": ["user", "business", "order", "payment", "product", "domain", "marketing", "content", "social"],
        "401": ["backend", "gateway", "api", "service", "bff", "microservice", "message queue", "cache"],
        "501": ["data", "database", "mysql", "postgresql", "nosql", "redis", "warehouse"],
        "601": ["component", "tool", "library", "framework", "scaffold"],
        "701": ["ai", "artificial intelligence", "machine learning", "blockchain", "game", "embedded"],
        "901": ["ops", "deployment", "monitor", "ci/cd", "docker", "k8s", "pipeline", "environment"]
    }
    
    # Simple weight calculation based on prefix and keywords
    best_ccc = None
    max_matches = 0
    
    for ccc, keywords in mapping.items():
        matches = sum(1 for k in keywords if k in text)
        if matches > max_matches:
            max_matches = matches
            best_ccc = ccc
            
    if best_ccc:
        return best_ccc
        
    # Default fallbacks
    default_map = {
        "RQ": "101",
        "DS": "201",
        "ADR": "101",
        "TK": "201"
    }
    return default_map.get(prefix, "101")


def _resolve_ccc(args: argparse.Namespace, prefix: str) -> str:
    """Resolve CCC code, inferring from project intro if not provided."""
    if args.ccc:
        return args.ccc
        
    intro_text = ""
    
    # 1. Check --intro provided via command line
    if hasattr(args, "intro") and args.intro:
        intro_text = args.intro
    else:
        # 2. Check baseline documents in project
        intro_files = [
            SPECS_DIR / "govs/G02-项目宪章.md",
            SPECS_DIR / "1-reqs/requirements.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "tmp/ideas.md"
        ]
        for f in intro_files:
            if f.exists():
                intro_text += read_text_safe(f) + "\n"
                
    if not intro_text.strip():
        log_warning("Project introduction not provided and no baseline documents found, using default CCC code.")
        log_info("Recommendation: provide --intro parameter or create specs/govs/G02-项目宪章.md first.")
        
    return _infer_ccc_from_text(intro_text, prefix)


def _get_all_existing_ids() -> set[str]:
    """Retrieve all existing document reference IDs."""
    checker = DocumentCodingChecker(SPECS_DIR)
    existing_ids = set()
    for root, _, files in os.walk(SPECS_DIR):
        for file in files:
            ref_id = checker.extract_reference_id(file)
            if ref_id:
                existing_ids.add(ref_id)
    return existing_ids


def create_requirement(args: argparse.Namespace) -> int:
    """Create requirement document and refresh index.
    
    Filename format: RQ-<CCC><NN>-<SLUG>需求.md
    Example: RQ-10102-用户注册需求.md
    """
    slug = args.slug
    if not slug:
        log_error("Missing requirement short description parameter")
        return 1
    
    ccc = _resolve_ccc(args, "RQ")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"1-reqs/RQ-{ccc}{nn}-{slug}需求.md"
    return _create_from_template("templates/req.template.md", target)


def create_design(args: argparse.Namespace) -> int:
    """Create design document and refresh index.
    
    Filename format: DS-<CCC><NN>-<SLUG>设计.md
    Example: DS-20101-API网关认证设计.md
    """
    slug = args.slug
    if not slug:
        log_error("Missing design short description parameter")
        return 1
    
    ccc = _resolve_ccc(args, "DS")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"2-designs/DS-{ccc}{nn}-{slug}设计.md"
    return _create_from_template("templates/design.template.md", target)


def create_adr(args: argparse.Namespace) -> int:
    """Create ADR document and refresh index.
    
    Filename format: ADR-<CCC><NN>-<SLUG>决策.md
    Example: ADR-10101-引入Redis缓存决策.md
    """
    slug = args.slug
    if not slug:
        log_error("Missing decision short description parameter")
        return 1
    
    ccc = _resolve_ccc(args, "ADR")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"adrs/ADR-{ccc}{nn}-{slug}决策.md"
    return _create_from_template("templates/adr.template.md", target)


def create_task(args: argparse.Namespace) -> int:
    """Create task document and refresh index.
    
    Filename format: TK-<CCC><YYWW><NN>-<SLUG>任务.md
    Example: TK-201260901-前端页面开发任务.md
    """
    slug = args.slug
    if not slug:
        log_error("Missing task short description parameter")
        return 1
    
    ccc = _resolve_ccc(args, "TK")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    yyww = get_yyww()
    
    target = f"3-tasks/TK-{ccc}{yyww}{nn}-{slug}任务.md"
    return _create_from_template("templates/task.template.md", target)


def create_test(args: argparse.Namespace) -> int:
    """Create test document and refresh index."""
    scope_slug = validating_slug_value(args.scope, "scope")
    if scope_slug is None:
        return 1
    test_id_slug = validating_slug_value(args.test_id, "test_id")
    if test_id_slug is None:
        return 1
    target = f"tests/test-{scope_slug}-{test_id_slug}.md"
    return _create_from_template("templates/test.template.md", target)


def create_release(args: argparse.Namespace) -> int:
    """Create release document and refresh index."""
    if not validating_semver(args.version):
        return 1
    target = f"releases/release-{get_current_date_slug()}-v{args.version}.md"
    return _create_from_template("templates/release.template.md", target)


def generate_traceability_matrix(_: argparse.Namespace) -> int:
    """Generate and update traceability matrix (JSON/Markdown)."""
    json_path, md_path, req_count = generate_traceability_outputs(SPECS_DIR)
    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"Generated: {json_path}")
    log_info(f"Updated: {md_path}")
    log_info(f"Traceability matrix entries: {req_count}")
    return 0


def generate_agent_dispatch(_: argparse.Namespace) -> int:
    """Generate unified Agent/Skill dispatch rules."""
    target, warnings, errors = write_agent_dispatch_file(SPECS_DIR)
    for warning in warnings:
        log_warning(warning)
    for error in errors:
        log_error(error)

    if errors:
        return 1

    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"Generated: {target}")
    return 0


def _reading_agent_dispatch_payload() -> tuple[dict[str, object], list[str], list[str]]:
    """Read or instantly build dispatch rule payload."""
    dispatch_path = SPECS_DIR / "meta/index/agent-dispatch.json"
    if dispatch_path.exists():
        try:
            payload = json.loads(read_text_safe(dispatch_path))
            return payload, [], []
        except json.JSONDecodeError as exc:
            log_warning(f"Dispatch rule JSON parsing failed, falling back to instant build: {exc}")
    return build_agent_dispatch_payload(SPECS_DIR)


def resolve_agent_dispatch_command(args: argparse.Namespace) -> int:
    """Resolve task dispatch recommendations based on Agent/Skill definitions."""
    payload, warnings, errors = _reading_agent_dispatch_payload()
    for warning in warnings:
        log_warning(warning)
    for error in errors:
        log_error(error)

    if errors:
        return 1

    result = resolve_agent_dispatch(
        payload=payload,
        task=args.task,
        stage=args.stage,
        requested_skills=args.skills,
    )

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    log_info(f"Primary Agent: {result['primary_agent']}")
    log_info(f"Recommended Skills: {', '.join(result['recommended_skills']) or '(None)'}")
    log_info(f"Support Agents: {', '.join(result['support_agents']) or '(None)'}")
    for reason in result["primary_reasons"]:
        log_info(f"Dispatch Basis: {reason}")
    for rule in result["shared_skill_arbitration"]:
        log_info(f"Shared Skill Arbitration: {rule.get('skill')} -> {rule.get('rule')}")
    return 0


def _parsing_extra_entries(raw_items: list[str] | None) -> list[tuple[str, str]]:
    """Parse `--extra-entry path:format` parameter list."""
    parsed: list[tuple[str, str]] = []
    for raw in raw_items or []:
        if ":" not in raw:
            raise ValueError(f"extra-entry format error (requires path:format): {raw}")
        path, fmt = raw.split(":", 1)
        path = path.strip()
        fmt = fmt.strip()
        if not path or not fmt:
            raise ValueError(f"extra-entry format error (empty field): {raw}")
        parsed.append((path, fmt))
    return parsed


def generate_tool_adapters(_: argparse.Namespace) -> int:
    """Generate/sync multi-tool entry artifacts."""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    manifest_path = write_tool_adapter_manifest(REPO_ROOT, manifest)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)
    log_info(f"Written adapter manifest: {manifest_path}")
    log_info(f"Synced entry artifacts: {', '.join(written_entries) or '(None)'}")
    log_info(f"Manifest path: {MANIFEST_REL_PATH}")
    return 0


def list_tool_adapters_command(_: argparse.Namespace) -> int:
    """List multi-tool adapter manifest."""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    rows = list_tool_adapters(manifest)
    if not rows:
        log_warning("No tool adapter items configured")
        return 0

    log_info("Tool Adapter Manifest:")
    for row in rows:
        log_info(
            " | ".join(
                [
                    f"tool={row['tool_id']}",
                    f"name={row['display_name']}",
                    f"enabled={row['enabled']}",
                    f"format={row['definition_format']}",
                    f"entries={row['entries']}",
                ]
            )
        )
    return 0


def add_tool_adapter_command(args: argparse.Namespace) -> int:
    """Add a new tool to the multi-tool adapter manifest."""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    try:
        extra_entries = _parsing_extra_entries(args.extra_entry)
        manifest = add_tool_adapter(
            manifest=manifest,
            tool_id=args.tool_id,
            display_name=args.display_name,
            entry_file=args.entry_file,
            entry_format=args.entry_format,
            shared_entry=args.shared_entry,
            extra_entries=extra_entries,
        )
    except ValueError as exc:
        log_error(str(exc))
        return 1

    write_tool_adapter_manifest(REPO_ROOT, manifest)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)
    log_info(f"Added tool adapter: {args.tool_id}")
    log_info(f"Synced entry artifacts: {', '.join(written_entries) or '(None)'}")
    return 0


def remove_tool_adapter_command(args: argparse.Namespace) -> int:
    """Remove a tool from the multi-tool adapter manifest."""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    try:
        manifest, removable_paths = remove_tool_adapter(manifest, args.tool_id)
    except ValueError as exc:
        log_error(str(exc))
        return 1

    write_tool_adapter_manifest(REPO_ROOT, manifest)
    deleted_paths = delete_entry_files(REPO_ROOT, removable_paths)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)

    log_info(f"Removed tool adapter: {args.tool_id}")
    log_info(f"Recycled entry artifacts: {', '.join(deleted_paths) or '(None)'}")
    log_info(f"Current entry artifacts: {', '.join(written_entries) or '(None)'}")
    return 0


def check_spec_status(_: argparse.Namespace) -> int:
    """Check if required specification files are complete."""
    file_code = check_required_files(SPECS_DIR, REQUIRED_SPEC_FILES)
    if file_code != 0:
        return file_code

    issues: list[str] = []
    for rel, section, labels in [
        ("1-reqs/requirements.md", "Metadata", ("Document ID", "Version", "Owner", "Date")),
        ("2-designs/architecture.md", "Metadata", ("Document ID", "Version", "Owner", "Date")),
        ("3-tasks/task-plan.md", "Task List", ("Task ID", "Description", "Owner", "Acceptance Criteria", "Status")),
        ("tests/test-plan.md", "Metadata", ("Document ID", "Version", "Owner", "Date")),
        ("releases/release-plan.md", "Metadata", ("Version", "Owner", "Date")),
        ("changelogs/CHANGELOG.md", "Version Info", ("Version", "Date", "Release Owner")),
        ("runbook/runbook.md", "Metadata", ("Document ID", "Version", "Owner", "Date")),
    ]:
        path = SPECS_DIR / rel
        for issue in check_required_nonempty_bullets(path, section, labels):
            issues.append(f"{path} -> {issue}")

    if issues:
        log_error("Main artifacts have placeholder or missing content:")
        for issue in issues:
            log_error(f"- {issue}")
        return 1
    log_info("Completeness check passed")
    return 0


def check_requirement_doc(_: argparse.Namespace) -> int:
    """Validate content structure of main requirement document."""
    return check_requirement_file(SPECS_DIR / "1-reqs/requirements.md")


def check_design_doc(_: argparse.Namespace) -> int:
    """Validate content structure of main architecture design document."""
    return check_design_file(SPECS_DIR / "2-designs/architecture.md")


def check_changelog(_: argparse.Namespace) -> int:
    """Check if changelog file exists and is not empty."""
    return check_changelog_file(SPECS_DIR / "changelogs/CHANGELOG.md")


def build_governance_token_requirements() -> dict[str, list[str]]:
    """Build required fields and key text rules for governance checks."""
    return {
        "govs/G04-角色职责.md": [
            "Major changes and releases: Jointly signed by Owner and Reviewing Agent.",
            "Pre-release validation: Testing Agent is responsible for verifying factual output, not final release approval.",
            "Release execution: Release Agent is responsible for execution and archiving, not final release approval.",
        ],
        "govs/G05-Agent协作宪章.md": [
            "Release approval is jointly signed by Owner and Reviewer role; Testing role only provides validation facts, Release role only executes release.",
        ],
        "govs/G03-质量门禁.md": [
            "Release approval status satisfied (Joint signature by Owner + reviewer-agent).",
            "### Role Responsibilities",
            "tester-agent: provides validation results and risk classification.",
            "reviewer-agent: provides blocking/release recommendations and participates in joint signature.",
            "release-agent: executes approved release and archiving.",
            "## One-page RACI (REL-Gate)",
        ],
        "releases/release-plan.md": [
            "## Approval Records",
            "- Owner Approval:",
            "- reviewer-agent Approval:",
            "- Joint Signature Conclusion:",
            "- Approval Time:",
        ],
        "templates/release.template.md": [
            "## Approval Records",
            "- Owner Approval:",
            "- reviewer-agent Approval:",
            "- Joint Signature Conclusion:",
            "- Approval Time:",
        ],
        "meta/index/capability-matrix.md": [
            "## Metadata",
            "| Capability | Document | Priority | Maturity | Owner | Dependencies | Status |",
            "| Agent | Primary Capability | Priority | Maturity | Dependency Skill | Status |",
            "| Skill | Primary Agent | Priority | Maturity | Dependencies | Status |",
        ],
    }


def check_governance_token_files(required_tokens_by_file: dict[str, list[str]]) -> list[str]:
    """Check if required tokens in key governance files are complete."""
    issues: list[str] = []
    for rel, tokens in required_tokens_by_file.items():
        path = SPECS_DIR / rel
        code = check_path_exists(path, "Missing governance file: {path}", "Governance file is empty: {path}")
        if code != 0:
            issues.append(f"missing:{path}")
            continue

        text = read_text_safe(path)
        for token in tokens:
            if token not in text:
                issues.append(f"Missing governance field: {path} -> {token}")
    return issues


def check_governance_release_records(required_release_labels: set[str]) -> list[str]:
    """Check if approval fields in release records are complete."""
    issues: list[str] = []
    for path in sorted((SPECS_DIR / "releases").glob("release-*.md")):
        issues.extend(check_structured_bullets(path, "Approval Records", required_release_labels, "Release Approval"))
    return issues


def check_governance_metadata_sections(required_metadata_labels: set[str]) -> list[str]:
    """Check if metadata fields in governance and role documents are complete."""
    issues: list[str] = []
    metadata_targets: list[Path] = []
    metadata_targets.extend(sorted((SPECS_DIR / "govs").glob("*.md")))
    metadata_targets.extend(sorted((SPECS_DIR / "agents").glob("*.md")))
    metadata_targets.extend(sorted((SPECS_DIR / "skills").glob("*.md")))
    for path in metadata_targets:
        issues.extend(check_structured_bullets(path, "Metadata", required_metadata_labels, "Metadata"))
    return issues


def check_governance(_: argparse.Namespace) -> int:
    """Execute governance approval chain integrity check."""
    required_tokens_by_file = build_governance_token_requirements()
    required_release_labels = {
        normalize_md_token("Owner Approval"),
        normalize_md_token("reviewer-agent Approval"),
        normalize_md_token("Joint Signature Conclusion"),
        normalize_md_token("Approval Time"),
    }
    required_metadata_labels = {
        normalize_md_token("Version"),
        normalize_md_token("Effective Date"),
        normalize_md_token("Last Updated"),
        normalize_md_token("Change Description"),
    }

    issues: list[str] = []
    issues.extend(check_governance_token_files(required_tokens_by_file))
    issues.extend(check_governance_release_records(required_release_labels))
    issues.extend(check_governance_metadata_sections(required_metadata_labels))

    failed = False
    for issue in issues:
        if issue.startswith("missing:"):
            failed = True
            continue
        log_error(issue)
        failed = True

    if failed:
        return 1

    log_info("Governance approval chain check passed")
    return 0


def check_spec_drift(_: argparse.Namespace) -> int:
    """Check consistency between code and specification source markers."""
    return check_drift_files(REPO_ROOT, SUPPORTED_CODE_SUFFIXES, SPEC_MARK)


def check_project_dependencies(_: argparse.Namespace) -> int:
    """Execute dependency risk and reproducibility checks."""
    return check_dependencies(REPO_ROOT)


def check_project_code_quality(_: argparse.Namespace) -> int:
    """Execute lightweight code quality checks."""
    return check_code_quality(REPO_ROOT)


def check_spec_completeness(_: argparse.Namespace) -> int:
    """Check requirement chain completeness after refreshing traceability matrix."""
    generate_traceability_outputs(SPECS_DIR)
    return check_completeness(SPECS_DIR)


def check_doc_naming(_: argparse.Namespace) -> int:
    """Check specification document naming conventions and index registration completeness."""
    index_file = SPECS_DIR / "meta/index/index.md"
    index_text = read_text_safe(index_file) if index_file.exists() else ""
    index_registered_files = extract_registered_ids(index_text)
    has_structured_file_section = "## Files" in index_text

    failed = False
    for file in sorted(SPECS_DIR.rglob("*")):
        if not file.is_file():
            continue
        if "__pycache__" in file.parts:
            continue

        rel = file.relative_to(SPECS_DIR).as_posix()
        if file.name in ("README.md", "INDEX.md") or is_ccc_coded(file.name): continue
        checker = NamingChecker(BANNED_NAMES, SPECIAL_MARKDOWN_NAMES)
        issues = checker.validate_path(file, rel)
        if issues:
            failed = True
            for issue in issues:
                log_error(issue)
            if any("Unsupported tool file type" in issue or "Unsupported file type" in issue for issue in issues):
                continue

        if rel != "meta/index/index.md" and index_text:
            if has_structured_file_section:
                if rel not in index_registered_files:
                    log_error(f"Not registered in index: {file}")
                    failed = True
            elif f"`{rel}`" not in index_text:
                log_error(f"Not registered in index: {file}")
                failed = True

    if failed:
        return 1

    log_info("Naming check passed")
    return 0


def check_document_coding(_: argparse.Namespace) -> int:
    """Check document coding standards (CCC-NN-YYWW system)."""
    checker = _getting_document_coding_checker()
    passed, errors, warnings = checker.check_all()
    
    if errors:
        log_error(f"Found {len(errors)} coding errors:")
        for error in errors:
            log_error(f"  - {error}")
    
    if warnings:
        log_warning(f"Found {len(warnings)} warnings:")
        for warning in warnings:
            log_warning(f"  - {warning}")
    
    if passed and not errors:
        log_info("Document coding standards check passed")
        return 0
    
    return 1 if errors else 0


def locate_document(args: argparse.Namespace) -> int:
    """Locate document based on document reference ID."""
    checker = _getting_document_coding_checker()
    ref_id = args.ref_id
    
    # Validate reference ID format
    # For RQ-10102 format, extract RQ
    # For G01 format, extract G (letter part)
    if '-' in ref_id:
        prefix = ref_id.split('-')[0]
    else:
        # G01, S01 format, extract first letter
        prefix = ref_id[0] if ref_id else ""
    
    valid_prefixes = ['RQ', 'DS', 'TK', 'ADR', 'G', 'S']
    if prefix not in valid_prefixes:
        log_error(f"Invalid document reference ID format: {ref_id}")
        log_error(f"Supported types: {', '.join(valid_prefixes)}")
        return 1
    
    path, error, matches = checker.locate_document(ref_id)
    
    if error:
        log_error(error)
        return 1
    
    if not path:
        log_error(f"Document reference ID not found: {ref_id}")
        return 1
    
    # Output relative path
    rel_path = path.relative_to(REPO_ROOT)
    print(str(rel_path))
    return 0


def read_document(args: argparse.Namespace) -> int:
    """Read document content based on document reference ID."""
    ref_id = args.ref_id
    
    path, error, matches = resolve_spec_path(ref_id)
    
    if error:
        log_error(error)
        return 1
    
    if not path:
        log_error(f"Document reference ID not found: {ref_id}")
        return 1
    
    # Read and output document content
    try:
        content = read_text_safe(path)
        print(content)
        return 0
    except Exception as exc:
        log_error(f"Failed to read document: {exc}")
        return 1


def trace_document_dependencies(args: argparse.Namespace) -> int:
    """Trace document dependencies (associated requirements, designs, tasks, code)."""
    ref_id = args.ref_id
    
    # Execute dependency tracing
    result = trace_dependencies(SPECS_DIR, ref_id, REPO_ROOT)
    
    if result.errors:
        for error in result.errors:
            log_error(error)
        return 1
    
    # Output format selection
    if hasattr(args, 'as_json') and args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    
    # Output readable format
    _print_dependency_trace(result)
    return 0


def _print_dependency_trace(result) -> None:
    """Print dependency trace results (human-readable format)."""
    print(f"\n{'='*70}")
    print(f"Document Dependency Trace: {result.ref_id}")
    print(f"{'='*70}")
    
    # Source document info
    if result.source_doc:
        print("\n📄 Source Document:")
        print(f"   ID: {result.source_doc.doc_id}")
        print(f"   Title: {result.source_doc.doc_title}")
        print(f"   Path: {result.source_doc.doc_path}")
        print(f"   Type: {result.source_doc.doc_type}")
    
    # Associated requirements
    if result.related_reqs:
        print(f"\n📋 Associated Requirements ({len(result.related_reqs)}):")
        for doc in result.related_reqs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     Path: {doc.doc_path}")
            if doc.context:
                print(f"     Context: {doc.context}")
    
    # Associated designs
    if result.related_designs:
        print(f"\n🎨 Associated Designs ({len(result.related_designs)}):")
        for doc in result.related_designs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     Path: {doc.doc_path}")
            if doc.context:
                print(f"     Context: {doc.context}")
    
    # Associated tasks
    if result.related_tasks:
        print(f"\n📌 Associated Tasks ({len(result.related_tasks)}):")
        for doc in result.related_tasks:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     Path: {doc.doc_path}")
            if doc.context:
                print(f"     Context: {doc.context}")
    
    # Associated tests
    if result.related_tests:
        print(f"\n🧪 Associated Tests ({len(result.related_tests)}):")
        for doc in result.related_tests:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     Path: {doc.doc_path}")
            if doc.context:
                print(f"     Context: {doc.context}")
    
    # Associated ADRs
    if result.related_adrs:
        print(f"\n🏛️ Associated Architecture Decisions ({len(result.related_adrs)}):")
        for doc in result.related_adrs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     Path: {doc.doc_path}")
            if doc.context:
                print(f"     Context: {doc.context}")
    
    # Code references
    if result.code_refs:
        print(f"\n💻 Code Implementation ({len(result.code_refs)}):")
        for ref in result.code_refs:
            print(f"   • {ref.file_path}:{ref.line_number}")
            if ref.module_name:
                print(f"     Module: {ref.module_name}")
            if ref.function_name:
                print(f"     Function/Class: {ref.function_name}")
            print(f"     Context: {ref.context}")
    elif result.source_doc and result.source_doc.doc_type == "requirement":
        print("\n⚠️ Code implementation reference not found")
        print(f"   Hint: ensure code contains '{result.ref_id}' or '{SPEC_MARK}' markers")
    
    print(f"\n{'='*70}\n")


def rename_document(args: argparse.Namespace) -> int:
    """Rename document or change document reference ID.
    
    Supports two usage modes:
    1. Pass full filename: rename-document "old_filename.md" "new_filename.md"
    2. Pass reference ID: rename-document --by-ref-id "RQ-10102" "new_filename.md"
    """
    checker = _getting_document_coding_checker()
    
    # Determine whether to use reference ID or full filename
    if hasattr(args, 'by_ref_id') and args.by_ref_id:
        # Locate file via reference ID
        path, error, matches = resolve_spec_path(args.old_identifier)
        
        if error:
            log_error(error)
            return 1
        
        if not path:
            log_error(f"Document reference ID not found: {args.old_identifier}")
            return 1
        
        old_filename = path.name
    else:
        # Use full filename directly
        old_filename = args.old_identifier
    
    success, message = checker.rename_document(old_filename, args.new_filename)
    
    if success:
        log_info(message)
        # Refresh index after renaming
        index_code = refresh_index_after_change()
        if index_code != 0:
            return index_code
        return 0
    else:
        log_error(message)
        return 1


def collect_governance_capabilities() -> list[tuple[str, str, str]]:
    """Collect governance capability matrix row data."""
    rows: list[tuple[str, str, str]] = []
    for capability_id, rel in [
        ("G01", "govs/G01-治理与流程.md"),
        ("G02", "govs/G02-项目宪章.md"),
        ("G03", "govs/G03-质量门禁.md"),
        ("G04", "govs/G04-角色职责.md"),
        ("G05", "govs/G05-Agent协作宪章.md"),
    ]:
        path = SPECS_DIR / rel
        if not path.exists():
            continue
        title = read_first_heading(path) or path.stem
        rows.append((capability_id, rel, title))
    return rows


def collect_agent_capabilities() -> list[tuple[str, str, str]]:
    """Collect Agent capability matrix row data."""
    return _collect_capabilities_from_glob("agents", "*-agent.md", "AGENT")


def collect_skill_capabilities() -> list[tuple[str, str, str]]:
    """Collect Skill capability matrix row data."""
    return _collect_capabilities_from_glob("skills", "*-skill.md", "SKILL")


def _collect_capabilities_from_glob(
    directory: str,
    pattern: str,
    capability_prefix: str,
) -> list[tuple[str, str, str]]:
    """Collect capability matrix rows by directory and matching pattern."""
    rows: list[tuple[str, str, str]] = []
    files = sorted((SPECS_DIR / directory).glob(pattern))
    for idx, path in enumerate(files, start=1):
        rel = path.relative_to(SPECS_DIR).as_posix()
        title = read_first_heading(path) or path.stem
        rows.append((f"{capability_prefix}-{idx:03d}", rel, title))
    return rows


def generate_index(_: argparse.Namespace) -> int:
    """Generate and write full specification index document."""
    index = SPECS_DIR / "meta/index/index.md"
    markdown_counts = count_specs_by_dir(SPECS_DIR)

    lines: list[str] = ["# specs Master Index", "", "## Document Overview"]
    lines.extend(
        [
            "| Category | Directory | File Count | Core Capability | Status |",
            "|---|---|---:|---|---|",
        ]
    )

    for category, directory in CATEGORY_DIRECTORY_ROWS:
        count = markdown_counts.get(directory, 0)
        capability = "✅" if count > 0 else "⚪"
        status = "Complete" if count > 0 else "Pending"
        lines.append(f"| {category} | `{directory}/` | {count} | {capability} | {status} |")

    lines.extend(["", "## Core Capability List", ""])
    lines.extend(["### Governance Capabilities", "| ID | Document | Description | Status |", "|---|---|---|---|"])
    governance_rows = collect_governance_capabilities()
    if governance_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in governance_rows)
    else:
        lines.append("| - | - | None | ⚪ |")

    lines.extend(["", "### Agent Capabilities", "| ID | Document | Description | Status |", "|---|---|---|---|"])
    agent_rows = collect_agent_capabilities()
    if agent_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in agent_rows)
    else:
        lines.append("| - | - | None | ⚪ |")

    lines.extend(["", "### Skill Capabilities", "| ID | Document | Description | Status |", "|---|---|---|---|"])
    skill_rows = collect_skill_capabilities()
    if skill_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in skill_rows)
    else:
        lines.append("| - | - | None | ⚪ |")

    lines.extend(["", "## Directories"])
    lines.extend(f"- {name}" for name in list_top_directories())
    lines.extend(["", "## Files"])
    lines.extend(f"- `{rel}`" for rel in list_files_depth_two(SPECS_DIR))
    return write_index(index, lines)


def initialize_project(_: argparse.Namespace) -> int:
    """Initialize specification directory, templates, and baseline documents."""
    for directory in DIRECTORIES:
        (SPECS_DIR / directory).mkdir(parents=True, exist_ok=True)

    for rel, content in TEMPLATE_CONTENTS.items():
        write_file_safe(SPECS_DIR / rel, content)

    for rel, content in SEED_CONTENTS.items():
        write_file_safe(SPECS_DIR / rel, content)

    ensure_gov_metadata()
    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"specs initialization complete: {SPECS_DIR}")
    return 0


def build_default_handlers() -> dict[str, CommandHandler]:
    """Build default command handler mapping."""
    return build_handler_map(
        {
            "initialize": initialize_project,
            "version": show_version,
            "generate-index": generate_index,
            "generate-traceability-matrix": generate_traceability_matrix,
            "generate-agent-dispatch": generate_agent_dispatch,
            "generate-tool-adapters": generate_tool_adapters,
            "create-requirement": create_requirement,
            "create-design": create_design,
            "create-adr": create_adr,
            "create-task": create_task,
            "create-test": create_test,
            "create-release": create_release,
            "check-status": check_spec_status,
            "check-quality-gates": check_quality_gates,
            "validate-requirement": check_requirement_doc,
            "validate-design": check_design_doc,
            "check-changelog": check_changelog,
            "check-governance": check_governance,
            "check-dependencies": check_project_dependencies,
            "check-code-quality": check_project_code_quality,
            "check-completeness": check_spec_completeness,
            "check-naming": check_doc_naming,
            "check-document-coding": check_document_coding,
            "bundle-task-context": bundle_task_context,
            "trace-code": trace_code_origins,
            "locate-document": locate_document,
            "read-document": read_document,
            "trace-dependencies": trace_document_dependencies,
            "rename-document": rename_document,
            "build-reference-index": build_reference_index,
            "find-references-to": find_references_to,
            "find-references-from": find_references_from,
            "update-references": update_references,
            "delete-references": delete_references,
            "check-orphaned-references": check_orphaned_references,
            "reference-report": generate_reference_report,
            "check-drift": check_spec_drift,
            "resolve-agent-dispatch": resolve_agent_dispatch_command,
            "list-tool-adapters": list_tool_adapters_command,
            "add-tool-adapter": add_tool_adapter_command,
            "remove-tool-adapter": remove_tool_adapter_command,
        }
    )


def build_reference_index(args: argparse.Namespace) -> int:
    """Build document reference index."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    manager.scan_all_references()
    manager.save_index()
    
    index = manager.build_reference_index()
    stats = index.get('stats', {})
    
    log_info("Reference index build complete:")
    log_info(f"  - Total references: {stats.get('total_references', 0)}")
    log_info(f"  - Total source files: {stats.get('total_source_files', 0)}")
    log_info(f"  - Total target files: {stats.get('total_target_files', 0)}")
    log_info(f"  - Index file: {manager.index_path.relative_to(REPO_ROOT)}")
    
    return 0


def find_references_to(args: argparse.Namespace) -> int:
    """Query which documents reference a specified reference ID."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    refs = manager.find_references_to(args.ref_id)
    
    if not refs:
        print(f"No documents found referencing {args.ref_id}")
        return 0
    
    print(f"\nDocuments referencing {args.ref_id} ({len(refs)} total):\n")
    
    # Group by source file
    by_source: dict = {}
    for ref in refs:
        source = ref['source_file']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(ref)
    
    for source, items in sorted(by_source.items()):
        print(f"📄 {source}")
        for item in items:
            print(f"   Line {item['line_number']}: {item['context'][:80]}...")
        print()
    
    return 0


def find_references_from(args: argparse.Namespace) -> int:
    """Query which documents are referenced by a specified document."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    refs = manager.find_references_from(args.ref_id)
    
    if not refs:
        print(f"{args.ref_id} does not reference other documents")
        return 0
    
    print(f"\nDocuments referenced by {args.ref_id} ({len(refs)} total):\n")
    
    # Group by type
    by_type: dict = {}
    for ref in refs:
        ref_type = ref.get('ref_type', 'doc')
        if ref_type not in by_type:
            by_type[ref_type] = []
        by_type[ref_type].append(ref)
    
    for ref_type, items in sorted(by_type.items()):
        type_name = {'doc': '📄 Document Reference', 'index': '📑 Index Reference', 'code': '💻 Code Reference'}.get(ref_type, ref_type)
        print(f"{type_name}:")
        for item in items:
            print(f"   - {item['target_ref_id']} ({item['target_file']})")
        print()
    
    return 0


def update_references(args: argparse.Namespace) -> int:
    """Batch update reference relationships."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    
    count, log = manager.update_references(
        args.old_ref_id, 
        args.new_ref_id, 
        dry_run=args.dry_run
    )
    
    for line in log:
        if args.dry_run:
            print(line)
        else:
            if line.startswith("Error"):
                log_error(line)
            else:
                log_info(line)
    
    if not args.dry_run and count > 0:
        log_info(f"Updated {count} references total")
    
    return 0 if not any(line.startswith("Error") for line in log) else 1


def delete_references(args: argparse.Namespace) -> int:
    """Delete references to a specified document."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    
    count, log = manager.delete_references_to(args.ref_id, dry_run=args.dry_run)
    
    for line in log:
        if args.dry_run:
            print(line)
        else:
            if line.startswith("Error"):
                log_error(line)
            else:
                log_info(line)
    
    return 0


def check_orphaned_references(args: argparse.Namespace) -> int:
    """Check for orphaned references."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    orphaned = manager.check_orphaned_references()
    
    if not orphaned:
        log_info("No orphaned references found")
        return 0
    
    log_warning(f"Found {len(orphaned)} orphaned references:")
    for item in orphaned:
        print(f"  - {item['source_file']}:{item['line_number']}")
        print(f"    Reference Target: {item['target_file']}")
        print(f"    Suggestion: {item['suggestion']}")
    
    return 0


def generate_reference_report(args: argparse.Namespace) -> int:
    """Generate document reference relationship report."""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    report = manager.generate_reference_report()
    
    print(report)
    
    # Save report
    report_path = SPECS_DIR / "meta/index" / "reference-report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    log_info(f"\nReport saved to: {report_path.relative_to(REPO_ROOT)}")
    
    return 0


def bundle_task_context(args: argparse.Namespace) -> int:
    """Aggregate task-related context (requirements, designs, ADRs) into tmp directory."""
    task_id = args.task_id.upper()
    if not task_id.startswith("TK-"):
        log_error(f"Invalid Task ID: {task_id} (must start with TK-)")
        return 1

    # 1. Locate task document
    task_path, error_msg, _ = resolve_spec_path(task_id)
    if error_msg:
        log_error(error_msg)
        return 1
    if not task_path:
        log_error(f"Task document not found: {task_id}")
        return 1

    log_info(f"Aggregating task context: {task_id} <- {task_path.name}")

    # 2. Parse associated references in task document
    content = read_text_safe(task_path)
    # Match RQ-10101, DS-20101, ADR-10101, TEST-10101 etc.
    ref_pattern = re.compile(r"\b([A-Z]{1,4}-[A-Z0-9-]+)\b")
    found_refs = ref_pattern.findall(content)
    
    # Filter duplicates and exclude self
    unique_refs = []
    seen = {task_id}
    for ref in found_refs:
        # Special handling for DS- prefix, as resolve_spec_path expects DS- or DS-XXX
        # In our specification DSN might be abbreviated as DS
        search_ref = ref
        if ref.startswith("DS-"):
            search_ref = ref.replace("DS-", "DS-")
            
        if search_ref not in seen:
            unique_refs.append(search_ref)
            seen.add(search_ref)

    # 3. Aggregate content
    output_lines = [
        f"# Task Context Aggregation: {task_id}",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Original Task File: {task_path.name}",
        "",
        "> [!IMPORTANT]",
        "> This file is automatically generated by SDD tools for development context only. **Do not modify this file directly**; all changes should be made in corresponding source documents under `specs/`.",
        "",
        "---",
        "## [TASK] Task Definition",
        content,
        "",
    ]

    for ref in unique_refs:
        doc_path, _, _ = resolve_spec_path(ref)
        if doc_path and doc_path.exists():
            log_info(f"  + Aggregating associated document: {ref}")
            doc_content = read_text_safe(doc_path)
            
            # Determine document type
            doc_type = "DOC"
            if ref.startswith("RQ"):
                doc_type = "REQUIREMENT"
            elif ref.startswith("DS"):
                doc_type = "DESIGN"
            elif ref.startswith("ADR"):
                doc_type = "ADR"
            elif ref.startswith("TEST"):
                doc_type = "TEST"

            output_lines.extend([
                "---",
                f"## [{doc_type}] {ref} ({doc_path.name})",
                doc_content,
                "",
            ])
        else:
            log_warning(f"  ! Skipping associated document not found: {ref}")

    # 4. Write to tmp directory
    tmp_dir = REPO_ROOT / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    output_file = tmp_dir / f"TASK-CONTEXT-{task_id}.md"
    
    try:
        output_file.write_text("\n".join(output_lines), encoding="utf-8")
        log_info(f"Context aggregation complete: {output_file.relative_to(REPO_ROOT)}")
        print(f"\n[SUCCESS] Context bundled at: {output_file.relative_to(REPO_ROOT)}\n")
        return 0
    except Exception as e:
        log_error(f"Failed to write aggregated file: {e}")
        return 1


def check_quality_gates(args: argparse.Namespace) -> int:
    """Execute comprehensive quality gate checks. Aggregates naming, drift, and completeness checks."""
    log_info(">>> Executing SDD Quality Gate verification...")
    
    # 1. Refresh index and traceability matrix (base)
    if generate_index(args) != 0:
        return 1
    if generate_traceability_matrix(args) != 0:
        return 1

    # 2. Execute core verifications
    failed = False
    
    log_info("\n[1/3] Checking naming standards and index registration...")
    if check_doc_naming(args) != 0:
        failed = True

    log_info("\n[2/3] Checking specification drift and reference validity...")
    if check_spec_drift(args) != 0:
        failed = True

    log_info("\n[3/3] Checking full-link completeness (REQ -> DSN -> TK -> CODE)...")
    if check_spec_completeness(args) != 0:
        failed = True

    print("\n" + "="*60)
    if failed:
        log_error("Quality gate verification failed! Please fix the above issues before continuing.")
    print("\n" + "="*60)
    if failed:
        log_error("Quality gate verification failed! Please fix the above issues before continuing.")
        print("="*60 + "\n")
        return 1
    else:
        log_info("Congratulations! All quality gate verifications passed.")
        print("="*60 + "\n")
        return 0


def show_version(_: argparse.Namespace) -> int:
    """Show the current version of the SDD toolchain and governance system."""
    from sdd.config import SDD_TOOL_VERSION

    # 1. Extract governance version (G01)
    gov_version = "Unknown"
    gov_path = SPECS_DIR / "govs/G01-治理与流程.md"
    if gov_path.exists():
        content = read_text_safe(gov_path)
        match = re.search(r"- 版本：\s*(v[0-9.]+)", content)
        if match:
            gov_version = match.group(1)

    # 2. Extract standards version (S01)
    std_version = "Unknown"
    std_path = SPECS_DIR / "standards/S01-文档编码规范.md"
    if std_path.exists():
        content = read_text_safe(std_path)
        match = re.search(r"- 版本：\s*(v[0-9.]+)", content)
        if match:
            std_version = match.group(1)

    print(f"\n{'='*40}")
    print(" SDD System Version Report")
    print(f"{'='*40}")
    print(f"  > Toolchain Version (Tooling):  {SDD_TOOL_VERSION}")
    print(f"  > Governance Policy (Policy):     {gov_version}")
    print(f"  > Document Specification (Standard):   {std_version}")
    print(f"{'='*40}\n")
    
    return 0


def trace_code_origins(args: argparse.Namespace) -> int:
    """Reverse-trace original requirements, designs, and tasks from code file annotations."""
    code_path = Path(args.file_path).resolve()
    if not code_path.exists():
        log_error(f"Code file does not exist: {code_path}")
        return 1

    try:
        rel_to_root = code_path.relative_to(REPO_ROOT)
    except ValueError:
        rel_to_root = code_path

    log_info(f"Tracing specification sources from code: {rel_to_root}")
    
    content = read_text_safe(code_path)
    # Match specification ID format
    ref_pattern = re.compile(r"\b([A-Z]{1,4}-[A-Z0-9-]+)\b")
    found_ids = ref_pattern.findall(content)
    
    if not found_ids:
        log_warning("No specification reference markers (e.g., RQ-xxx, DS-xxx) found in this file")
        return 0

    unique_ids = sorted(list(set(found_ids)))
    
    print(f"\n{'='*60}")
    print(f" Code Traceability Report: {code_path.name}")
    print(f"{'='*60}\n")

    for ref_id in unique_ids:
        # Special handling for DS -> DSN
        search_id = ref_id
        if ref_id.startswith("DS-"):
            search_id = ref_id.replace("DS-", "DS-")
            
        doc_path, _, _ = resolve_spec_path(search_id)
        if doc_path and doc_path.exists():
            title = read_first_heading(doc_path)
            rel_path = doc_path.relative_to(SPECS_DIR)
            print(f"  [{ref_id}] -> {title}")
            print(f"    Location: specs/{rel_path}")
            
            # Try to extract owner or version from metadata
            doc_text = read_text_safe(doc_path)
            meta_lines = doc_text.split("## Metadata", 1)[-1].split("##", 1)[0].splitlines()
            for line in meta_lines:
                if "Owner" in line or "Version" in line or "Status" in line:
                    print(f"    {line.strip().lstrip('-').strip()}")
            print("-" * 40)
        else:
            # Ignore words that look like IDs but are not specification IDs
            pass

    print("\n[INFO] Trace complete. To view details, run: sddtool.py read-document <ID>")
    return 0


def _getting_document_coding_checker() -> DocumentCodingChecker:
    """Initialize and return a DocumentCodingChecker instance."""
    return DocumentCodingChecker(str(SPECS_DIR))


def check_path_exists(path: Path, missing_msg: str, empty_msg: str) -> int:
    """Check if a path exists and is not empty, logging errors if not."""
    if not path.exists():
        log_error(missing_msg.format(path=path))
        return 1
    if not read_text_safe(path).strip():
        log_error(empty_msg.format(path=path))
        return 1
    return 0


__all__ = [
    "add_tool_adapter_command",
    "build_default_handlers",
    "check_changelog",
    "check_design_doc",
    "check_doc_naming",
    "check_document_coding",
    "check_governance",
    "check_project_code_quality",
    "check_project_dependencies",
    "check_requirement_doc",
    "check_spec_completeness",
    "check_spec_drift",
    "check_spec_status",
    "bundle_task_context",
    "show_version",
    "trace_code_origins",
    "locate_document",
    "read_document",
    "trace_document_dependencies",
    "rename_document",
    "create_adr",
    "create_design",
    "create_release",
    "create_requirement",
    "create_task",
    "create_test",
    "generate_index",
    "generate_agent_dispatch",
    "generate_tool_adapters",
    "generate_traceability_matrix",
    "initialize_project",
    "list_tool_adapters_command",
    "remove_tool_adapter_command",
    "resolve_agent_dispatch_command",
    "build_reference_index",
    "find_references_to",
    "find_references_from",
    "update_references",
    "delete_references",
    "check_orphaned_references",
    "generate_reference_report",
]
