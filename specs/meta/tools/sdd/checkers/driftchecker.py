"""
Specification drift checker, ensuring code files contain specification source markers.

## Specification References

This checker implements validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Sections |
|------------------------|--------------|---------------------|
| Coding Specification   | S02          | Audit and Evidence  |
| Evidence Specification | S06          | Evidence Association|

### S02 Coding Specification Requirements
- Execution evidence (review records, reports, checklists, or logs) must be retained.
- Evidence must be associated with the corresponding task, change, or release record.

### S06 Evidence Specification Requirements
- Code implementation must be traceable to the specification source.
- Drift (inconsistency between code and specification) must be detected and corrected.

## Implementation Mapping

| Method | Specification Requirement | Specification Section |
|--------|---------------------------|-----------------------|
| `_collecting_missing_paths()` | Collect files with missing markers | S06 Evidence Association |
| `running()` | Execute drift check | S02 Audit Evidence |

See also:
- specs/standards/S02-编码规范.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import re
from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error, log_info


class DriftChecker:
    """
    Check whether code files have specification source markers.

    Specification References:
    - S02 Coding Specification: Audit and Evidence
    - S06 Evidence Specification: Evidence Association

    Functions:
    1. Scan code files in the src/ directory.
    2. Check if files contain specification source markers (e.g., `Spec:`, etc.).
    3. Report files with missing markers.

    Purposes:
    - Prevent drift between code and specifications.
    - Ensure code implementation is traceable to requirements/designs.
    """

    def __init__(self, repo_root: Path, supported_suffixes: set[str], spec_mark: str) -> None:
        """Initialize the drift checker."""
        self.repo_root = repo_root
        self.supported_suffixes = supported_suffixes
        self.spec_mark = spec_mark

    def _collecting_missing_paths(self, src_dir: Path) -> list[str]:
        """Collect paths of code files missing specification markers or referencing invalid IDs."""
        issues: list[str] = []
        # Match formats like Spec: RQ-10101
        spec_pattern = re.compile(rf"{re.escape(self.spec_mark)}\s*([A-Z0-9-]+)")

        from sdd.utils import resolve_spec_path

        for path in src_dir.rglob("*"):
            if not path.is_file() or path.suffix not in self.supported_suffixes:
                continue
            content = read_text_safe(path)
            
            matches = spec_pattern.findall(content)
            if not matches:
                issues.append(f"Missing specification marker: {path}")
                continue
            
            for ref_id in matches:
                doc_path, error_msg, _ = resolve_spec_path(ref_id)
                if error_msg:
                    issues.append(f"Invalid reference [{ref_id}]: {path} ({error_msg})")
                elif not doc_path:
                    issues.append(f"Reference not found [{ref_id}]: {path}")
                    
        return issues

    def running(self) -> int:
        """Execute the drift check."""
        src_dir = self.repo_root / "src"
        if not src_dir.is_dir():
            log_info("src/ not found, skipping consistency check")
            return 0

        issues = self._collecting_missing_paths(src_dir)
        if issues:
            log_error("Specification consistency check found issues:")
            for item in issues:
                log_error(item)
            return 1

        log_info("Consistency check passed")
        return 0


def check_spec_drift(repo_root: Path, supported_suffixes: set[str], spec_mark: str) -> int:
    """Compatibility function entry point: execute code drift check."""
    return DriftChecker(repo_root, supported_suffixes, spec_mark).running()
