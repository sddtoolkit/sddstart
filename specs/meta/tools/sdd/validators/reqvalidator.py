"""
Requirement document validator, checks if key sections are complete.

## Specification Reference

This validator implements the validation logic for the following specifications:

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Document Specification | S03 | Requirement Document Structure |
| Quality Assurance | S04 | Requirement Verification |

### S03-Document Specification Requirements
- Requirement document must contain: Metadata, Goals and Scope, Functional Requirements, Acceptance Criteria, Traceability
- Metadata must contain: Document ID, Version, Owner, Date

### S04-Quality Assurance Requirements
- Requirements must be traceable to Design, Tasks, Tests
- Functional requirements should use FR-* identifier
- Acceptance criteria should use AC-* identifier

## Implementation Mapping

| Constant/Method | Specification Requirement | Specification Section |
|-----------|----------|----------|
| `REQUIRED_SECTIONS` | Requirement document required sections | S03-Requirement Structure |
| `check_requirement_file()` | Requirement document validation entry point | S04-Requirement Verification |

See:
- specs/standards/S03-Document Specification.md
- specs/standards/S04-Quality Assurance.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_error
from sdd.validators.sectionvalidator import (
    check_any_nonempty_prefixed_bullet,
    check_markdown_sections,
    check_required_nonempty_bullets,
)

# Specification Reference: S03-Document Specification - Requirement document required sections
REQUIRED_SECTIONS = (
    "## 元信息",
    "## 目标与范围",
    "## 功能需求",
    "## 验收标准",
    "## 追踪",
)


class RequirementValidator:
    """
    Validate the structural integrity of a single requirement document.

    Specification Reference:
    - S03 Document Specification: Requirement Document Structure
    - S04 Quality Assurance: Requirement Verification

    Checking Rules:
    1. Required sections: Metadata, Goals and Scope, Functional Requirements, Acceptance Criteria, Traceability
    2. Metadata fields: Document ID, Version, Owner, Date
    3. Goals and Scope fields: Goal, Scope
    4. Traceability fields: Associated Design, Associated Tasks, Associated Tests
    5. Functional Requirements: At least one FR-* entry
    6. Acceptance Criteria: At least one AC-* entry
    """

    def __init__(self, path: Path) -> None:
        """Initialize requirement document validator."""
        self.path = path

    def running(self) -> int:
        """Execute requirement document validation."""
        section_code = check_markdown_sections(
            path=self.path,
            subject="Requirement Document",
            required_sections=REQUIRED_SECTIONS,
            missing_sections_message="Requirement document is missing key sections:",
            passed_message="Requirement document check passed",
        )
        if section_code != 0:
            return section_code

        issues: list[str] = []
        issues.extend(check_required_nonempty_bullets(self.path, "元信息", ("文档编号", "版本", "负责人", "日期")))
        issues.extend(check_required_nonempty_bullets(self.path, "目标与范围", ("目标", "范围")))
        issues.extend(check_required_nonempty_bullets(self.path, "追踪", ("关联设计", "关联任务", "关联测试")))
        issues.extend(check_any_nonempty_prefixed_bullet(self.path, "功能需求", "FR-", "FR-*"))
        issues.extend(check_any_nonempty_prefixed_bullet(self.path, "验收标准", "AC-", "AC-*"))

        if issues:
            log_error("Requirement document has placeholder or missing content:")
            for issue in issues:
                log_error(f"- {issue}")
            return 1
        return 0


def check_requirement_file(path: Path) -> int:
    """Compatibility entry point: validate requirement document."""
    return RequirementValidator(path).running()
