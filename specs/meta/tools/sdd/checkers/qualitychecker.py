"""
Code quality checker, providing lightweight static quality signals.

## Specification References

This checker implements the validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Section |
|------------------------|--------------|--------------------|
| Coding Standards       | S02          | Code Organization, Logging, and Observability |
| Quality Assurance      | S04          | Code Review        |
| Operational Resilience | S09          | Observability Baseline |

### S02-Coding Standards Requirements
- Module boundaries must be clear, with single responsibility.
- Public interfaces must be documented or explained with comments.

### S04-Quality Assurance Requirements
- Critical modules must pass review before merging.
- Reviews must record conclusions and lists of issues.

### S09-Operational Resilience Requirements
- Code implementation must provide key path instrumentation.
- Maintain correlatable request identifiers.

## Implementation Mapping

| Constant/Method | Spec Requirement | Spec Section |
|-----------------|------------------|--------------|
| `MAX_WARN_LINE` | Line length warning threshold | S02-Code Style |
| `MAX_ERROR_LINE` | Line length error threshold | S02-Code Style |
| `MAX_ERROR_FILE_LINES` | File length threshold | S02-Code Organization |
| `TODO_MARK_PATTERN` | TODO/FIXME detection | S04-Review Check |

See also:
- specs/standards/S02-Coding-Standards.md
- specs/standards/S04-Quality-Assurance.md
- specs/standards/S09-Operational-Resilience.md
"""

from __future__ import annotations

import re
from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error, log_info, log_warning

# ============================================================================
# Code Quality Thresholds
# ============================================================================
# Spec Ref: S02-Coding Standards

# Supported code file suffixes
CODE_SUFFIXES = {".py", ".js", ".ts", ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp"}

# Line length thresholds (number of characters)
MAX_WARN_LINE = 120   # Warning if exceeded
MAX_ERROR_LINE = 200  # Error if exceeded

# File line count threshold
MAX_ERROR_FILE_LINES = 2000  # Error if exceeded

# TODO/FIXME marker patterns
TODO_MARK_PATTERN = re.compile(r"\b(?:TODO|FIXME)\b")

# C-style comment language suffixes
C_STYLE_SUFFIXES = {".js", ".ts", ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp"}


class QualityChecker:
    """Execute code length, line length, and TODO/FIXME quality checks."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the quality checker."""
        self.repo_root = repo_root

    @staticmethod
    def extract_c_style_comment_fragment(line: str, in_block: bool) -> tuple[str, bool]:
        """Extract C-style comment text fragments and return whether still within a block comment."""
        comment_parts: list[str] = []
        cursor = 0

        while cursor < len(line):
            if in_block:
                end = line.find("*/", cursor)
                if end == -1:
                    comment_parts.append(line[cursor:])
                    return "".join(comment_parts), True
                comment_parts.append(line[cursor:end])
                cursor = end + 2
                in_block = False
                continue

            line_start = line.find("//", cursor)
            block_start = line.find("/*", cursor)
            candidates = [pos for pos in (line_start, block_start) if pos != -1]
            if not candidates:
                break
            start = min(candidates)
            if start == line_start:
                comment_parts.append(line[start + 2 :])
                break
            end = line.find("*/", start + 2)
            if end == -1:
                comment_parts.append(line[start + 2 :])
                in_block = True
                break
            comment_parts.append(line[start + 2 : end])
            cursor = end + 2

        return "".join(comment_parts), in_block

    @staticmethod
    def check_todo_marker_in_comment(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
        """Determine if the current line's comments contain TODO/FIXME markers."""
        if suffix == ".py":
            hash_idx = line.find("#")
            comment_fragment = line[hash_idx + 1 :] if hash_idx != -1 else ""
            return bool(TODO_MARK_PATTERN.search(comment_fragment)), in_block

        if suffix in C_STYLE_SUFFIXES:
            comment_fragment, updated_in_block = QualityChecker.extract_c_style_comment_fragment(line, in_block)
            return bool(TODO_MARK_PATTERN.search(comment_fragment)), updated_in_block

        return False, in_block

    def collect_code_roots(self) -> list[Path]:
        """Collect common code directories that require quality checks."""
        roots = [self.repo_root / name for name in ("src", "app", "lib", "services")]
        return [p for p in roots if p.is_dir()]

    def running(self) -> int:
        """Execute the code quality check."""
        roots = self.collect_code_roots()
        if not roots:
            log_info("No code directories found (src/app/lib/services), skipping quality check")
            return 0

        warnings: list[str] = []
        errors: list[str] = []

        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in CODE_SUFFIXES:
                    continue

                text = read_text_safe(path)
                lines = text.splitlines()

                if len(lines) > MAX_ERROR_FILE_LINES:
                    errors.append(f"{path}: file too long ({len(lines)} lines)")

                todo_count = 0
                in_block_comment = False
                for idx, line in enumerate(lines, start=1):
                    has_todo, in_block_comment = self.check_todo_marker_in_comment(
                        line,
                        path.suffix,
                        in_block_comment,
                    )
                    if has_todo:
                        todo_count += 1
                    length = len(line)
                    if length > MAX_ERROR_LINE:
                        errors.append(f"{path}:{idx} line too long ({length})")
                    elif length > MAX_WARN_LINE:
                        warnings.append(f"{path}:{idx} line is long ({length})")

                if todo_count > 0:
                    warnings.append(f"{path}: {todo_count} TODO/FIXME markers found")

        if warnings:
            log_warning("Code quality warnings:")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("Code quality check failed:")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("Code quality check passed")
        return 0


def _extract_c_style_comment_fragment(line: str, in_block: bool) -> tuple[str, bool]:
    """Compatibility function entry point: extract C-style comment text fragments."""
    return QualityChecker.extract_c_style_comment_fragment(line, in_block)


def _check_todo_marker_in_comment(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
    """Compatibility function entry point: determine TODO/FIXME in comments."""
    return QualityChecker.check_todo_marker_in_comment(line, suffix, in_block)


def _collecting_code_roots(repo_root: Path) -> list[Path]:
    """Compatibility function entry point: collect code directories."""
    return QualityChecker(repo_root).collect_code_roots()


def check_code_quality(repo_root: Path) -> int:
    """Compatibility function entry point: execute code quality check."""
    return QualityChecker(repo_root).running()
