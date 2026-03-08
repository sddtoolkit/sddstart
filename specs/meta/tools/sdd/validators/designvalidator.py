"""
Design document validator, checks if key sections are complete.

## Specification Reference

This validator implements the validation logic for the following specifications:

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Document Specification | S03 | Design Document Structure |
| Quality Assurance | S04 | Design Verification |
| Security Specification | S02-Security | Security and Privacy |

### S03-Document Specification Requirements
- Design document must contain: Metadata, System Boundary/Architecture Overview, Security and Privacy, Reliability and Performance, Traceability
- Metadata must contain: Document ID, Version, Owner, Date

### S04-Quality Assurance Requirements
- Design must associate with requirements (Associated Requirements)
- Design must associate with tasks (Associated Tasks)

## Implementation Mapping

| Constant/Method | Specification Requirement | Specification Section |
|-----------|----------|----------|
| `REQUIRED_SECTIONS` | Design document required sections | S03-Design Structure |
| `ALTERNATIVE_SECTION_GROUPS` | Optional section groups | S03-Design Structure |
| `check_design_file()` | Design document validation entry point | S04-Design Verification |

See:
- specs/standards/S03-Document Specification.md
- specs/standards/S04-Quality Assurance.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error
from sdd.validators.sectionvalidator import (
    check_markdown_sections,
    check_required_nonempty_bullets,
)

# Specification Reference: S03-Document Specification - Design document required sections
REQUIRED_SECTIONS = (
    "## 元信息",
    "## 安全与隐私",
    "## 可靠性与性能",
    "## 追踪",
)

# Specification Reference: S03-Document Specification - Optional section groups (at least one must be present)
ALTERNATIVE_SECTION_GROUPS = (
    ("## 系统边界", "## 架构概览"),
    ("## 接口列表", "## 接口与契约"),
)


class DesignValidator:
    """
    Validate the structural integrity of a single design document.

    Specification Reference:
    - S03 Document Specification: Design Document Structure
    - S04 Quality Assurance: Design Verification

    Checking Rules:
    1. Required sections: Metadata, Security and Privacy, Reliability and Performance, Traceability
    2. Optional section groups (at least one): System Boundary/Architecture Overview, Interface List/Interfaces and Contracts
    3. Metadata fields: Document ID, Version, Owner, Date
    4. System Boundary fields: Boundary Definition, External Dependencies
    5. Architecture Overview fields: System Boundary, Key Components
    6. Interface fields: External Interfaces
    7. Security and Privacy fields: Authentication and Authorization, Data Protection
    8. Reliability and Performance fields: Capacity and Performance Goals
    9. Traceability fields: Associated Requirements, Associated Tasks
    """

    def __init__(self, path: Path) -> None:
        """Initialize design document validator."""
        self.path = path

    def running(self) -> int:
        """Execute design document validation."""
        section_code = check_markdown_sections(
            path=self.path,
            subject="Architecture Design",
            required_sections=REQUIRED_SECTIONS,
            missing_sections_message="Design document is missing key sections:",
            passed_message="Design document check passed",
            alternative_section_groups=ALTERNATIVE_SECTION_GROUPS,
        )
        if section_code != 0:
            return section_code

        text = read_text_safe(self.path)
        issues: list[str] = []
        issues.extend(check_required_nonempty_bullets(self.path, "元信息", ("文档编号", "版本", "负责人", "日期")))
        if "## 系统边界" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "系统边界", ("边界定义", "外部依赖")))
        if "## 架构概览" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "架构概览", ("系统边界", "关键组件")))
        if "## 接口列表" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "接口列表", ("对外接口",)))
        if "## 接口与契约" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "接口与契约", ("对外接口",)))
        issues.extend(check_required_nonempty_bullets(self.path, "安全与隐私", ("认证与授权", "数据保护")))
        issues.extend(check_required_nonempty_bullets(self.path, "可靠性与性能", ("容量与性能目标",)))
        issues.extend(check_required_nonempty_bullets(self.path, "追踪", ("关联需求", "关联任务")))

        if issues:
            log_error("Design document has placeholder or missing content:")
            for issue in issues:
                log_error(f"- {issue}")
            return 1
        return 0


def check_design_file(path: Path) -> int:
    """Compatibility entry point: validate design document."""
    return DesignValidator(path).running()
