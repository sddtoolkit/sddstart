"""
Changelog checker, validating that the log file exists and is not empty.

## Specification References

| Specification Document | Reference ID | Applicable Sections |
|------------------------|--------------|---------------------|
| Versioning Specification | S10          | Change Records      |
| Quality Assurance      | S04          | Change Tracking     |
| Evidence Specification | S06          | Change Evidence     |

### S10 Versioning Specification Requirements
- Changelog must record version changes.
- Changelog format must comply with conventions.

### S04 Quality Assurance Requirements
- Changes must be logged.
- Changelog must not be empty.

### S06 Evidence Specification Requirements
- Change records must exist as evidence.
- Change records must be associated with specific changes.

## Implementation Mapping

| Class/Method | Specification Requirement | Specification Section |
|--------------|---------------------------|-----------------------|
| `ChangelogChecker` | Changelog checker | S04 Change Tracking |
| `running()` | Execute changelog check | S10 Change Records |

See also:
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
- specs/standards/S10-版本号规范.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.io import check_file_integrity
from sdd.log import log_error, log_info


class ChangelogChecker:
    """
    Check the validity of the changelog file.

    Specification References:
    - S04 Quality Assurance: Change Tracking
    - S06 Evidence Specification: Change Evidence
    - S10 Versioning Specification: Change Records

    Functions:
    1. Check if the changelog file exists.
    2. Check if the changelog file is not empty.
    """

    def __init__(self, path: Path) -> None:
        """Initialize the changelog checker."""
        self.path = path

    def running(self) -> int:
        """Execute the changelog check."""
        ok, error_message = check_file_integrity(self.path, "Changelog")
        if not ok:
            log_error(error_message)
            return 1
        log_info("Changelog check passed")
        return 0


def check_changelog_file(path: Path) -> int:
    """Compatibility function entry point: check the changelog file."""
    return ChangelogChecker(path).running()
