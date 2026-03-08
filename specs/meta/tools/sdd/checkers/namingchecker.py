"""
SDD naming convention validation engine.

[SDD Traceability]
- Standard: S01 (Document Coding Standard)
- Standard: S02 (Coding Standard)
"""

from __future__ import annotations

import re
from pathlib import Path

# List of special configuration file exemptions
# Spec Ref: S01-7.1 (Tool Specifications)
SPECIAL_CONFIG_FILES = {
    "govs/knowledge-sources.yaml",
    "meta/index/traceability.json",
    "meta/index/agent-dispatch.json",
    "meta/index/tool-adapters.json",
    "meta/index/reference-index.json",
}

# CCC coding prefixes
CCC_PREFIXES = ('RQ-', 'DS-', 'TK-', 'ADR-', 'G', 'S')


class NamingChecker:
    """
    Responsible for validating whether project file names comply with SDD governance standards.
    
    Spec Ref: S01-6.1 (Format Validation)
    """

    def __init__(self, banned_names: set[str], special_markdown_names: set[str]) -> None:
        self.banned_names = banned_names
        self.special_markdown_names = special_markdown_names

    def validate_path(self, path: Path, rel_path: str) -> list[str]:
        """Perform a full validation of the compliance of a given path."""
        if rel_path in SPECIAL_CONFIG_FILES:
            return []

        if path.name.lower() in self.banned_names:
            return [f"Banned filename: {rel_path}"]

        # Exempt Python internal files
        if path.name in ("__init__.py", "requirements.txt"):
            return []

        if path.is_dir():
            return self._validate_base_name(path.name, f"Directory name invalid: {rel_path}")

        # Directory-specific validation
        parts = Path(rel_path).parts
        if parts and parts[0] == "meta":
            return self._validate_meta_file(path, rel_path)
        elif parts and parts[0] == "tools":
            return self._validate_tool_file(path, rel_path)

        return self._validate_base_name(path.name, f"Naming style invalid: {rel_path}")

    def _validate_base_name(self, name: str, message: str) -> list[str]:
        """Validate basic naming rules (lowercase, no spaces, no underscores)."""
        if any(ch.isupper() for ch in name) or "_" in name or " " in name:
            return [message]
        if not re.fullmatch(r"^[a-z0-9\-.]+$", name):
            return [f"Illegal characters in name: {name}"]
        return []

    def _validate_meta_file(self, path: Path, rel: str) -> list[str]:
        """Validate metadata directory. Spec Ref: S01-7.1."""
        allowed_sub = ("agents", "skills", "index", "tools")
        parts = Path(rel).parts
        if len(parts) < 2 or parts[1] not in allowed_sub:
            return [f"Unauthorized meta subdirectory: {rel}"]
        
        if parts[1] == "tools":
            if path.suffix not in (".py", ".md", ".txt", ".json"):
                return [f"Unsupported tool file type: {rel}"]
        elif path.suffix != ".md":
            return [f"Meta content must be Markdown: {rel}"]
            
        return self._validate_base_name(path.name, f"Meta naming invalid: {rel}")

    def _validate_tool_file(self, path: Path, rel: str) -> list[str]:
        """Validate tool directory."""
        if path.suffix not in (".py", ".md", ".txt"):
            return [f"Invalid tool extension: {rel}"]
        return self._validate_base_name(path.name, f"Tool naming invalid: {rel}")


def is_ccc_coded(filename: str) -> bool:
    """Check if the file is a controlled CCC-coded file."""
    return any(filename.startswith(p) for p in CCC_PREFIXES)
