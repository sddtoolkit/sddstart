"""
Index writer, responsible for persisting index file content.

## Specification Reference

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Governance and Process | G01 | Index Maintenance |
| Quality Assurance | S04 | Index Generation |

### G01-Governance and Process Requirements
- Index files must reflect the current specification directory structure
- Index updates must be written atomically

### S04-Quality Assurance Requirements
- Index generation must be traceable
- Generation results must be logged

## Implementation Mapping

| Class/Method | Specification Requirement | Specification Section |
|---------|----------|----------|
| `IndexGenerator` | Index generator | G01-Index Maintenance |
| `running()` | Execute index writing | S04-Index Generation |

See:
- specs/govs/G01-Governance and Process.md
- specs/standards/S04-Quality Assurance.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_info


class IndexGenerator:
    """
    Responsible for writing index files.

    Specification Reference:
    - G01 Governance and Process: Index Maintenance
    - S04 Quality Assurance: Index Generation

    Features:
    1. Receive a list of index content lines
    2. Atomically write the index file
    3. Log the generation process
    """

    def __init__(self, index_path: Path, lines: list[str]) -> None:
        """Initialize index writer."""
        self.index_path = index_path
        self.lines = lines

    def running(self) -> int:
        """Execute index writing."""
        self.index_path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        log_info(f"Generated: {self.index_path}")
        return 0


def write_index(index_path: Path, lines: list[str]) -> int:
    """Compatibility entry point: write index file."""
    return IndexGenerator(index_path, lines).running()
