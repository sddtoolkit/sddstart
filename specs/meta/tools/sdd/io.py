"""
SDD Base IO Utility Toolkit.

[SDD Traceability]
- Policy: G01 (Governance and Process)
- Standard: S03 (Documentation Standards)
"""

from __future__ import annotations

from pathlib import Path
from sdd.log import log_warning


def read_text_safe(path: Path) -> str:
    """
    Safely read a text file, automatically handling encoding exceptions and supporting replacement mode.
    
    Spec Ref: S03-1.1 (Mandatory UTF-8 Encoding)
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        log_warning(f"Encoding Warning: {path} is not UTF-8 ({exc}). Using fallback.")
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError(f"Failed to read file: {path} ({exc})") from exc


def check_file_integrity(
    path: Path, 
    subject: str,
    missing_template: str = "Missing {subject}: {path}",
    empty_template: str = "{subject} is empty: {path}"
) -> tuple[bool, str]:
    """
    Check file integrity (whether it exists and is not empty).
    
    Spec Ref: S04-3.2 (Evidence Integrity Verification)
    """
    if not path.exists():
        return False, missing_template.format(subject=subject, path=path)
    if path.stat().st_size == 0:
        return False, empty_template.format(subject=subject, path=path)
    return True, ""
