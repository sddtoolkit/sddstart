"""
Completeness checker, verifying whether the traceability matrix links meet requirements.

## Specification References

This checker implements the validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Section |
|------------------------|--------------|--------------------|
| Quality Assurance      | S04          | Traceability Integrity |
| Delivery Control       | S05          | Pre-delivery Check |

### S04-Quality Assurance Requirements
- Requirements must be linked to designs and tests.
- Traceability links must be complete and verifiable.
- Missing links should be reported as errors.

### S05-Delivery Control Requirements
- Integrity check must be passed before delivery.
- REQ must be linked to designs, tasks, and tests.

## Implementation Mapping

| Method | Spec Requirement | Spec Section |
|--------|------------------|--------------|
| `REQUIRED_LINKS` | Required traceability links | S04-Traceability Integrity |
| `_load_matrix()` | Load traceability matrix | S04-Traceability Management |
| `running()` | Execute completeness validation | S05-Delivery Check |

See also:
- specs/standards/S04-Quality-Assurance.md
- specs/standards/S05-Delivery-Control.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict, cast

from sdd.io import read_text_safe
from sdd.log import log_error, log_info, log_warning
from sdd.utils import normalize_id


class TraceabilityLinks(TypedDict, total=False):
    """Link fields for a single REQ entry in the traceability matrix."""

    adrs: list[object]
    designs: list[object]
    tasks: list[object]
    tests: list[object]


TraceabilityMatrix = dict[str, TraceabilityLinks | object]


class CompletenessChecker:
    """
    Validate the completeness of REQ links in the traceability matrix.

    Spec Ref:
    - S04 Quality Assurance: Traceability integrity requirements
    - S05 Delivery Control: Pre-delivery checks

    Check Rules:
    1. Each REQ must be linked to designs.
    2. Each REQ must be linked to tasks.
    3. Each REQ must be linked to tests.
    4. ADR association is optional; a warning is issued if missing.

    Traceability ID Format:
    - REQ: rq-xxx
    - ADR: adr-xxx
    - DSN: ds-xxx
    - TSK: tk-xxx
    - TEST: test-xxx
    """

    # Traceability ID regex patterns
    ID_PATTERNS = {
        "reqs": re.compile(r"\brq-[a-z0-9-]+\b"),
        "adrs": re.compile(r"\badr-[a-z0-9-]+\b"),
        "designs": re.compile(r"\bds-[a-z0-9-]+\b"),
        "tasks": re.compile(r"\btk-[a-z0-9-]+\b"),
        "tests": re.compile(r"\btest-[a-z0-9-]+\b"),
    }

    # Directory mapping for traceability IDs
    DIRECTORY_BY_FIELD = {
        "reqs": "1-reqs",
        "adrs": "adrs",
        "designs": "2-designs",
        "tasks": "3-tasks",
        "tests": "tests",
    }

    # Spec Ref: S04-Traceability Integrity - Required link types for REQ
    REQUIRED_LINKS = (
        ("designs", "Design"),
        ("tasks", "Task"),
        ("tests", "Test"),
        ("implementations", "Implementation"),
    )

    def __init__(self, specs_dir: Path) -> None:
        """Initialize the completeness checker."""
        self.specs_dir = specs_dir

    def _load_matrix(self) -> TraceabilityMatrix | None:
        """Read and parse the traceability matrix JSON."""
        trace_path = self.specs_dir / "meta/index/traceability.json"
        if not trace_path.exists():
            log_error("Missing traceability.json, please run generate-traceability-matrix first")
            return None

        try:
            matrix = json.loads(read_text_safe(trace_path))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            log_error(f"Failed to parse traceability matrix: {exc}")
            return None

        if not isinstance(matrix, dict):
            log_error("Traceability matrix format error: root node must be an object")
            return None
        return cast(TraceabilityMatrix, matrix)

    def _collecting_directory_identifiers(self, field: str) -> set[str]:
        """Extract and normalize traceability identifiers of a specific category from the target directory."""
        directory = self.specs_dir / self.DIRECTORY_BY_FIELD[field]
        if not directory.exists():
            return set()

        pattern = self.ID_PATTERNS[field]
        prefix = {
            "reqs": "RQ",
            "adrs": "ADR",
            "designs": "DS",
            "tasks": "TK",
            "tests": "TEST",
        }[field]
        identifiers: set[str] = set()
        for path in sorted(directory.rglob("*.md")):
            text = read_text_safe(path)
            for raw in pattern.findall(text):
                identifiers.add(normalize_id(raw, prefix))
        return identifiers

    def _collecting_existing_identifiers(self) -> dict[str, set[str]]:
        """Collect the set of existing identifiers for each category (REQ/ADR/DSN/TSK/TEST)."""
        ids = {field: self._collecting_directory_identifiers(field) for field in self.DIRECTORY_BY_FIELD}
        # Implementations don't have a corresponding specs directory; we assume if they are recorded 
        # in traceability.json, they are valid. Their validity is guaranteed by TraceabilityGenerator.
        ids["implementations"] = set() 
        return ids

    def running(self) -> int:
        """Execute the completeness check."""
        matrix = self._load_matrix()
        if matrix is None:
            return 1

        if not matrix:
            log_error("Traceability matrix is empty: no verifiable REQ entries (req-*) found")
            log_error("Please establish REQ/DSN/TSK/TEST traceability identifiers in req/design/task/test documents first")
            return 1

        warnings: list[str] = []
        errors: list[str] = []
        existing_identifiers = self._collecting_existing_identifiers()

        for req_id, links in sorted(matrix.items()):
            if not isinstance(links, dict):
                errors.append(f"{req_id} traceability structure error (should be an object)")
                continue
            if req_id not in existing_identifiers["reqs"]:
                errors.append(f"{req_id} corresponding definition not found in 1-reqs")

            adrs = links.get("adrs", [])
            if not isinstance(adrs, list):
                errors.append(f"{req_id} adrs field type error (should be a list)")
            elif not adrs:
                warnings.append(f"{req_id} not linked to any ADR")
            else:
                for adr_id in adrs:
                    if not isinstance(adr_id, str):
                        errors.append(f"{req_id} adrs contains non-string entry")
                        continue
                    if adr_id not in existing_identifiers["adrs"]:
                        errors.append(f"{req_id} linked ADR does not exist: {adr_id}")

            for field, label in self.REQUIRED_LINKS:
                items = links.get(field, [])
                if not isinstance(items, list):
                    errors.append(f"{req_id} {field} field type error (should be a list)")
                elif not items:
                    errors.append(f"{req_id} missing {label} link")
                else:
                    for linked_id in items:
                        if not isinstance(linked_id, str):
                            errors.append(f"{req_id} {field} contains non-string entry")
                            continue
                        if field == "implementations":
                            # Implementation files are not under the specs directory, so skip existence check
                            continue
                        if linked_id not in existing_identifiers[field]:
                            errors.append(f"{req_id} linked {label} does not exist: {linked_id}")

        if warnings:
            log_warning("Completeness check warnings:")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("Completeness check failed:")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("Completeness check passed")
        return 0


def check_completeness(specs_dir: Path) -> int:
    """Compatibility function entry point: execute traceability completeness check."""
    return CompletenessChecker(specs_dir).running()
