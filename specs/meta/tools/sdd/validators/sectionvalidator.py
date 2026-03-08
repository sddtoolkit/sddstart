"""
Markdown section structure validation common logic.

## Specification Reference

This validator provides common section validation functionality, supporting the following specifications:

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Document Specification | S03 | Document Structure |
| Quality Assurance | S04 | Document Verification |

### S03-Document Specification Requirements
- Document must use Markdown format
- Section titles use `##` H2 headers
- Field lists use `- Field Name: Value` format

### S04-Quality Assurance Requirements
- Key fields must exist and be non-empty
- Document verification must be executable automatically

## Implementation Mapping

| Function | Specification Requirement | Specification Section |
|------|----------|----------|
| `check_markdown_sections()` | Required section validation | S03-Document Structure |
| `collecting_bullet_fields()` | Field list parsing | S03-Field Format |
| `check_required_nonempty_bullets()` | Required fields non-empty | S04-Document Verification |

See:
- specs/standards/S03-Document Specification.md
- specs/standards/S04-Quality Assurance.md
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from sdd.io import check_file_integrity, read_text_safe
from sdd.log import log_error, log_info
from sdd.utils import (
    extract_md_section, 
    normalize_md_token, 
    parse_bullet_list
)


def check_markdown_sections(
    path: Path,
    subject: str,
    required_sections: Sequence[str],
    missing_sections_message: str,
    passed_message: str,
    alternative_section_groups: Sequence[Sequence[str]] = (),
) -> int:
    """Verify Markdown document required sections and optional grouping sections."""
    ok, error_message = check_file_integrity(path, subject)
    if not ok:
        log_error(error_message)
        return 1

    text = read_text_safe(path)
    missing = [section for section in required_sections if section not in text]
    for group in alternative_section_groups:
        if not any(section in text for section in group):
            missing.append(f"({' or '.join(group)})")

    if missing:
        log_error(missing_sections_message)
        for section in missing:
            log_error(f"- {section}")
        return 1

    log_info(passed_message)
    return 0


def check_required_nonempty_bullets(path: Path, section: str, required_labels: Sequence[str]) -> list[str]:
    """Check if given fields exist and have non-empty values in a section."""
    issues: list[str] = []
    lines = extract_md_section(read_text_safe(path), section)
    if not lines:
        issues.append(f"Missing section: {section}")
        return issues

    fields = parse_bullet_list(lines)
    field_map: dict[str, list[str]] = {}
    for label, value in fields:
        field_map.setdefault(label, []).append(value)

    for required in required_labels:
        key = normalize_md_token(required)
        values = field_map.get(key)
        if not values:
            issues.append(f"{section} missing field: {required}")
            continue
        if not any(value for value in values):
            issues.append(f"{section} field is empty: {required}")
    return issues


def check_any_nonempty_prefixed_bullet(path: Path, section: str, prefix: str, display_name: str) -> list[str]:
    """Check if at least one non-empty field with a given prefix exists in a section."""
    lines = extract_md_section(read_text_safe(path), section)
    if not lines:
        return [f"Missing section: {section}"]

    normalized_prefix = normalize_md_token(prefix)
    for label, value in parse_bullet_list(lines):
        if label.startswith(normalized_prefix) and value:
            return []
    return [f"{section} missing non-empty field: {display_name}"]
