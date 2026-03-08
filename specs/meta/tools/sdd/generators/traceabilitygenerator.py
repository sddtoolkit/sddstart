"""
Generate traceability matrix from requirements to design/tasks/tests.

## Specification Reference

| Specification Document | Reference Number | Applicable Section |
|----------|----------|----------|
| Quality Assurance | S04 | Traceability Integrity |
| Evidence Specification | S06 | Evidence Association |
| Delivery Control | S05 | Pre-delivery Check |

### S04-Quality Assurance Requirements
- Requirements must be associated with designs and tests
- Traceability links must be complete and verifiable
- Traceability matrix must be generated automatically

### S06-Evidence Specification Requirements
- Evidence must be associated with corresponding tasks, changes, or release records
- Traceability identifiers must be unique and parsable

### S05-Delivery Control Requirements
- Traceability matrix integrity must be verified before delivery
- Missing links must be reported as errors

## Traceability Identifier Format

| Identifier Type | Format | Example |
|----------|------|------|
| REQ | req-xxx | req-user-auth |
| ADR | adr-xxx | adr-database-choice |
| DSN | dsn-xxx | dsn-api-gateway |
| TSK | tsk-xxx | tsk-impl-auth |
| TEST | test-xxx | test-login-flow |

## Implementation Mapping

| Constant/Class/Method | Specification Requirement | Specification Section |
|---------------|----------|----------|
| `ID_PATTERNS` | Traceability identifier regex patterns | S06-Identifier Format |
| `TRACEABLE_DIRECTORIES` | Traceable directory definitions | S04-Traceability Scope |
| `TraceabilityGenerator` | Traceability matrix generator | S04-Traceability Generation |
| `build_traceability_matrix()` | Aggregate associations by REQ | S04-Traceability Aggregation |

See:
- specs/standards/S04-Quality Assurance.md
- specs/standards/S05-交付控制.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sdd.config import REPO_ROOT, SUPPORTED_CODE_SUFFIXES
from sdd.io import read_text_safe
from sdd.utils import normalize_id

# Specification Reference: S06-Evidence Specification - Traceability identifier regex patterns
ID_PATTERNS = {
    "reqs": re.compile(r"\breq-[a-z0-9-]+\b"),
    "adrs": re.compile(r"\badr-[a-z0-9-]+\b"),
    "designs": re.compile(r"\bdsn-[a-z0-9-]+\b"),
    "tasks": re.compile(r"\btsk-[a-z0-9-]+\b"),
    "tests": re.compile(r"\btest-[a-z0-9-]+\b"),
}

# Specification Reference: S04-Quality Assurance - Traceable directory definitions
TRACEABLE_DIRECTORIES = (
    "1-reqs",
    "adrs",
    "2-designs",
    "3-tasks",
    "tests",
    "releases",
)


class TraceabilityGenerator:
    """
    Generate traceability matrix JSON and Markdown artifacts.

    Specification Reference:
    - S04 Quality Assurance: Traceability Integrity
    - S06 Evidence Specification: Evidence Association

    Features:
    1. Scan all documents in traceable directories
    2. Extract REQ/ADR/DSN/TSK/TEST identifiers
    3. Aggregate associations by REQ
    4. Generate traceability matrix in JSON and Markdown formats
    """

    def __init__(self, specs_dir: Path) -> None:
        """Initialize traceability matrix generator."""
        self.specs_dir = specs_dir

    @staticmethod
    def extract_identifiers(text: str, prefix: str) -> set[str]:
        """Extract traceability identifiers from document by prefix and filter gate placeholders."""
        key_map = {
            "RQ": "reqs",
            "ADR": "adrs",
            "DS": "designs",
            "TK": "tasks",
            "TEST": "tests",
        }
        key = key_map[prefix.upper()]
        pattern = ID_PATTERNS[key]
        normalized = {normalize_id(raw, prefix) for raw in pattern.findall(text)}
        return {item for item in normalized if not item.endswith("-GATE")}

    def collect_identifiers_by_file(self) -> list[dict[str, set[str]]]:
        """Scan traceable directories and extract relationship identifiers from each document."""
        rows: list[dict[str, set[str]]] = []
        for directory in TRACEABLE_DIRECTORIES:
            base_dir = self.specs_dir / directory
            if not base_dir.exists():
                continue
            for path in sorted(base_dir.rglob("*.md")):
                if "templates" in path.parts:
                    continue
                text = read_text_safe(path)
                rows.append(
                    {
                        "reqs": self.extract_identifiers(text, "RQ"),
                        "adrs": self.extract_identifiers(text, "ADR"),
                        "designs": self.extract_identifiers(text, "DS"),
                        "tasks": self.extract_identifiers(text, "TK"),
                        "tests": self.extract_identifiers(text, "TEST"),
                    }
                )
        return rows

    def scan_code_implementations(self) -> dict[str, set[str]]:
        """Scan code directories and extract Spec reference tags."""
        src_dir = REPO_ROOT / "src"
        implementations: dict[str, set[str]] = {}
        if not src_dir.is_dir():
            return implementations

        # Match Spec: RQ-10101 etc.
        spec_mark_pattern = re.compile(r"Spec:\s*([A-Z]{1,4}-[A-Z0-9-]+)")

        for path in src_dir.rglob("*"):
            if not path.is_file() or path.suffix not in SUPPORTED_CODE_SUFFIXES:
                continue
            
            content = read_text_safe(path)
            found_ids = spec_mark_pattern.findall(content)
            
            rel_path = str(path.relative_to(REPO_ROOT))
            for ref_id in found_ids:
                # Normalize ID
                prefix = ref_id.split("-")[0]
                norm_id = normalize_id(ref_id, prefix)
                implementations.setdefault(norm_id, set()).add(rel_path)
                
        return implementations

    def build_traceability_matrix(self) -> dict[str, dict[str, list[str]]]:
        """Aggregate ADR/Design/Task/Test/Code implementation reference relationships by REQ."""
        matrix: dict[str, dict[str, set[str]]] = {}
        
        # 1. Process document-to-document traceability
        for row in self.collect_identifiers_by_file():
            if not row["reqs"]:
                continue
            for req in row["reqs"]:
                entry = matrix.setdefault(
                    req,
                    {
                        "adrs": set(),
                        "designs": set(),
                        "tasks": set(),
                        "tests": set(),
                        "implementations": set(),
                    },
                )
                entry["adrs"].update(row["adrs"])
                entry["designs"].update(row["designs"])
                entry["tasks"].update(row["tasks"])
                entry["tests"].update(row["tests"])

        # 2. Process code implementation traceability (Code to RQ or Code to DS)
        code_refs = self.scan_code_implementations()
        
        # Associate code references with corresponding RQ
        for ref_id, files in code_refs.items():
            if ref_id.startswith("RQ-") and ref_id in matrix:
                matrix[ref_id]["implementations"].update(files)
        
        # If code references DS, find the corresponding RQ for the DS
        ds_to_reqs: dict[str, set[str]] = {}
        for req_id, links in matrix.items():
            for ds_id in links["designs"]:
                ds_to_reqs.setdefault(ds_id, set()).add(req_id)
        
        for ds_id, files in code_refs.items():
            if ds_id.startswith("DS-") and ds_id in ds_to_reqs:
                for req_id in ds_to_reqs[ds_id]:
                    matrix[req_id]["implementations"].update(files)

        normalized: dict[str, dict[str, list[str]]] = {}
        for req in sorted(matrix.keys()):
            normalized[req] = {
                "adrs": sorted(matrix[req]["adrs"]),
                "designs": sorted(matrix[req]["designs"]),
                "tasks": sorted(matrix[req]["tasks"]),
                "tests": sorted(matrix[req]["tests"]),
                "implementations": sorted(matrix[req]["implementations"]),
            }
        return normalized

    def write_traceability_json(self, matrix: dict[str, dict[str, list[str]]]) -> Path:
        """Write the traceability matrix to a JSON file."""
        path = self.specs_dir / "meta/index/traceability.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def write_traceability_markdown(self, matrix: dict[str, dict[str, list[str]]]) -> Path:
        """Write the traceability matrix to a readable Markdown table."""
        path = self.specs_dir / "meta/index/traceability.md"
        lines = ["# Traceability Matrix", "", "| REQ | ADR | DSN | TSK | TEST | CODE |", "|---|---|---|---|---|---|"]
        if matrix:
            for req, links in matrix.items():
                adrs = ", ".join(links["adrs"]) or "-"
                dsns = ", ".join(links["designs"]) or "-"
                tasks = ", ".join(links["tasks"]) or "-"
                tests = ", ".join(links["tests"]) or "-"
                code = ", ".join([Path(f).name for f in links.get("implementations", [])]) or "-"
                lines.append(f"| {req} | {adrs} | {dsns} | {tasks} | {tests} | {code} |")
        else:
            lines.append("| - | - | - | - | - | - |")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def running(self) -> tuple[Path, Path, int]:
        """Generate JSON and Markdown artifacts for the traceability matrix and return entry count."""
        matrix = self.build_traceability_matrix()
        json_path = self.write_traceability_json(matrix)
        md_path = self.write_traceability_markdown(matrix)
        return json_path, md_path, len(matrix)


def generate_traceability_outputs(specs_dir: Path) -> tuple[Path, Path, int]:
    """Generate traceability matrix artifacts."""
    return TraceabilityGenerator(specs_dir).running()
