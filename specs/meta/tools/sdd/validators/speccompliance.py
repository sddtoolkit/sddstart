"""
Specification compliance validator, checks if required documents exist and are non-empty.

## Specification Reference

This validator implements the validation logic for the following specifications:

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Governance and Process | G01 | Project Baseline |
| Quality Assurance | S04 | Completeness Check |

### G01-Governance and Process Requirements
- Project must have a complete specification directory structure
- Required documents must exist and be non-empty

### S04-Quality Assurance Requirements
- Existence of required files must be verified before delivery
- Empty files are considered non-compliant with the specification

## Implementation Mapping

| Class/Method | Specification Requirement | Specification Section |
|---------|----------|----------|
| `SpecComplianceValidator` | Specification compliance checker | G01-Project Baseline |
| `running()` | Execute required file check | S04-Completeness Check |

See:
- specs/govs/G01-Governance and Process.md
- specs/standards/S04-Quality Assurance.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_error, log_info


class SpecComplianceValidator:
    """
    Validate the existence and non-emptiness of required specification files.

    Specification Reference:
    - G01 Governance and Process: Project Baseline
    - S04 Quality Assurance: Completeness Check

    Features:
    1. Check if specified files exist
    2. Check if files are non-empty
    3. Report all missing or empty files
    """

    def __init__(self, specs_dir: Path, required_rel_paths: list[str]) -> None:
        """Initialize specification compliance checker."""
        self.specs_dir = specs_dir
        self.required_rel_paths = required_rel_paths

    def running(self) -> int:
        """Execute required file check."""
        missing = 0
        for rel in self.required_rel_paths:
            path = self.specs_dir / rel
            if not path.exists() or path.stat().st_size == 0:
                log_error(f"Missing or empty: {path}")
                missing = 1
        if missing:
            return 1
        log_info("Completeness check passed")
        return 0


def check_required_files(specs_dir: Path, required_rel_paths: list[str]) -> int:
    """Compatibility entry point: validate required specification files."""
    return SpecComplianceValidator(specs_dir, required_rel_paths).running()
