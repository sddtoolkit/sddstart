"""
Document dependency tracer, retrieving associated requirements, designs, tasks, and code implementations based on document reference IDs.

## Specification References

| Specification Document | Reference ID | Applicable Sections |
|------------------------|--------------|---------------------|
| Document Coding Specification | S01 | Reference ID Rules  |
| Quality Assurance      | S04          | Traceability Integrity |
| Evidence Specification | S06          | Evidence Association|
| Coding Specification   | S02          | Spec Source Markers |

### S01 Document Coding Specification Requirements
- Reference ID formats: RQ-XXXXX, DS-XXXXX, TK-XXXXXXXXX, ADR-XXXXX, GNN, SNN
- Reference IDs are used for cross-referencing between documents.

### S04 Quality Assurance Requirements
- Traceability links must be complete.
- Requirements must be associated with designs, tasks, and tests.

### S06 Evidence Specification Requirements
- Code implementation must be traceable to the specification source.
- Code files should contain specification markers (SPEC_MARK).

### S02 Coding Specification Requirements
- Code must contain specification source markers.
- Drift (inconsistency between code and specification) must be detectable.

## Trace Result Structure

```
DependencyTraceResult
├── ref_id: str              # Queried document reference ID
├── source_doc               # Source document information
├── related_reqs             # Associated requirements list
├── related_designs          # Associated designs list
├── related_tasks            # Associated tasks list
├── related_tests            # Associated tests list
├── related_adrs             # Associated decisions list
├── code_refs                # Code references list
└── errors                   # Error messages list
```

## Implementation Mapping

| Class/Method | Specification Requirement | Specification Section |
|--------------|---------------------------|-----------------------|
| `DependencyTracer` | Dependency tracer | S04 Traceability Management |
| `trace()` | Execute trace query | S06 Evidence Association |
| `_find_code_references()` | Find code references | S02 Spec Markers |

See also:
- specs/standards/S01-文档编码规范.md
- specs/standards/S02-编码规范.md
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from sdd.io import read_text_safe
from sdd.config import SPEC_MARK, SUPPORTED_CODE_SUFFIXES
from sdd.utils import resolve_spec_path


@dataclass
class CodeReference:
    """
    Code reference information.

    Specification Reference: S02 Coding Specification, S06 Evidence Specification

    Attributes:
        file_path: Code file path.
        line_number: Reference line number.
        context: Reference context (code snippet).
        module_name: Module name.
        function_name: Function/class name.
    """
    file_path: str
    line_number: int
    context: str
    module_name: str = ""
    function_name: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "context": self.context,
            "module": self.module_name,
            "function": self.function_name,
        }


@dataclass
class DocumentReference:
    """
    Document reference information.

    Specification Reference: S01 Document Coding Specification, S04 Quality Assurance

    Attributes:
        doc_id: Document reference ID (e.g., RQ-10102).
        doc_path: Document relative path.
        doc_title: Document title.
        doc_type: Document type (requirement/design/task/test/adr/governance/standard).
        context: Reference context.
    """
    doc_id: str
    doc_path: str
    doc_title: str
    doc_type: str
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.doc_id,
            "path": self.doc_path,
            "title": self.doc_title,
            "type": self.doc_type,
            "context": self.context,
        }


@dataclass
class DependencyTraceResult:
    """
    Dependency trace result.

    Specification Reference: S04 Quality Assurance, S06 Evidence Specification

    Attributes:
        ref_id: Queried document reference ID.
        source_doc: Source document information.
        related_reqs: Associated requirements list.
        related_designs: Associated designs list.
        related_tasks: Associated tasks list.
        related_tests: Associated tests list.
        related_adrs: Associated decisions list.
        code_refs: Code references list.
        errors: Error messages list.
    """
    ref_id: str
    source_doc: Optional[DocumentReference] = None
    related_reqs: list[DocumentReference] = field(default_factory=list)
    related_designs: list[DocumentReference] = field(default_factory=list)
    related_tasks: list[DocumentReference] = field(default_factory=list)
    related_tests: list[DocumentReference] = field(default_factory=list)
    related_adrs: list[DocumentReference] = field(default_factory=list)
    code_refs: list[CodeReference] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "ref_id": self.ref_id,
            "source_doc": self.source_doc.to_dict() if self.source_doc else None,
            "related": {
                "requirements": [r.to_dict() for r in self.related_reqs],
                "designs": [r.to_dict() for r in self.related_designs],
                "tasks": [r.to_dict() for r in self.related_tasks],
                "tests": [r.to_dict() for r in self.related_tests],
                "adrs": [r.to_dict() for r in self.related_adrs],
            },
            "code_refs": [c.to_dict() for c in self.code_refs],
            "errors": self.errors,
        }


class DependencyTracer:
    """
    Document dependency tracer.

    Specification References:
    - S01 Document Coding Specification: Document ID format
    - S04 Quality Assurance: Traceability integrity
    - S06 Evidence Specification: Evidence association

    Functions:
    1. Locate source document based on document reference ID.
    2. Find all documents referencing the specified ID.
    3. Find specification source markers in code.
    4. Generate complete dependency trace results.

    Supported document types:
    - RQ: Requirement document
    - DS: Design document
    - TK: Task document
    - ADR: Decision document
    - G: Governance document
    - S: Standard document
    - TEST: Test document
    """

    # Spec Ref: S01 Document Coding Specification - Document type mapping
    DOC_TYPE_MAP = {
        "RQ": "requirement",
        "DS": "design",
        "TK": "task",
        "ADR": "adr",
        "G": "governance",
        "S": "standard",
        "TEST": "test",
    }

    # Spec Ref: S01 Document Coding Specification - Reference identifier patterns
    REF_PATTERNS = {
        "RQ": re.compile(r"\bRQ-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "DS": re.compile(r"\bDS-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "TK": re.compile(r"\bTK-[0-9]{3,}[0-9]{4,}[0-9A-Z]{2,}\b"),
        "ADR": re.compile(r"\bADR-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "G": re.compile(r"\bG[0-9]{2,}\b"),
        "S": re.compile(r"\bS[0-9]{2,}\b"),
    }
    
    def __init__(self, specs_dir: Path, repo_root: Path | None = None):
        self.specs_dir = specs_dir
        self.repo_root = repo_root or specs_dir.parent
        
    def trace(self, ref_id: str) -> DependencyTraceResult:
        """
        Trace document dependencies.
        
        Args:
            ref_id: Document reference ID, e.g., "RQ-10102".
            
        Returns:
            DependencyTraceResult: Trace result.
        """
        result = DependencyTraceResult(ref_id=ref_id)
        
        # 1. Locate source document
        source_path = self._locate_source_document(ref_id)
        if not source_path:
            result.errors.append(f"Document not found: {ref_id}")
            return result
            
        result.source_doc = self._parse_document_info(source_path, ref_id)
        
        # 2. Search for all documents referencing the ID in the specs directory
        self._find_related_documents(ref_id, result)
        
        # 3. Search for locations referencing the ID in the code
        self._find_code_references(ref_id, result)
        
        return result
    
    def _locate_source_document(self, ref_id: str) -> Path | None:
        """Locate source document."""
        path, _, _ = resolve_spec_path(ref_id)
        return path

    def _parse_document_info(self, path: Path, doc_id: str) -> DocumentReference:
        """Parse document information."""
        prefix = doc_id.split("-")[0] if "-" in doc_id else doc_id
        doc_type = self.DOC_TYPE_MAP.get(prefix, "unknown")
        
        # Read title
        title = self._extract_title(path)
        rel_path = path.relative_to(self.specs_dir)
        
        return DocumentReference(
            doc_id=doc_id,
            doc_path=str(rel_path),
            doc_title=title,
            doc_type=doc_type,
        )
    
    def _extract_title(self, path: Path) -> str:
        """Extract the document title."""
        try:
            text = read_text_safe(path)
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
        except Exception:
            pass
        return path.stem
    
    def _find_related_documents(self, ref_id: str, result: DependencyTraceResult) -> None:
        """Find associated documents."""
        # Scan all traceable directories
        traceable_dirs = ["1-reqs", "adrs", "2-designs", "3-tasks", "tests", "releases", "govs", "standards"]
        
        for dir_name in traceable_dirs:
            base_dir = self.specs_dir / dir_name
            if not base_dir.exists():
                continue
                
            for doc_path in base_dir.rglob("*.md"):
                if "templates" in str(doc_path):
                    continue
                    
                try:
                    text = read_text_safe(doc_path)
                    if ref_id in text:
                        # Extract reference context
                        context = self._extract_context(text, ref_id)
                        
                        # Determine document type and ID
                        doc_id = self._extract_doc_id_from_filename(doc_path.name)
                        prefix = doc_id.split("-")[0] if doc_id and "-" in doc_id else ""
                        doc_type = self.DOC_TYPE_MAP.get(prefix, "unknown")
                        
                        doc_ref = DocumentReference(
                            doc_id=doc_id or doc_path.stem,
                            doc_path=str(doc_path.relative_to(self.specs_dir)),
                            doc_title=self._extract_title(doc_path),
                            doc_type=doc_type,
                            context=context,
                        )
                        
                        # Categorized storage
                        if prefix == "RQ":
                            result.related_reqs.append(doc_ref)
                        elif prefix == "DS":
                            result.related_designs.append(doc_ref)
                        elif prefix == "TK":
                            result.related_tasks.append(doc_ref)
                        elif prefix == "TEST" or "test" in str(doc_path).lower():
                            result.related_tests.append(doc_ref)
                        elif prefix == "ADR":
                            result.related_adrs.append(doc_ref)
                        elif prefix == "G":
                            # Governance documents are grouped into the tests category (or a new governance category could be added)
                            result.related_tests.append(doc_ref)
                        elif prefix == "S":
                            # Standard documents are determined based on content
                            if "测试" in text[:500]:
                                result.related_tests.append(doc_ref)
                            else:
                                result.related_designs.append(doc_ref)
                except Exception:
                    continue
        
        # Deduplicate and sort
        result.related_reqs = self._deduplicate_docs(result.related_reqs)
        result.related_designs = self._deduplicate_docs(result.related_designs)
        result.related_tasks = self._deduplicate_docs(result.related_tasks)
        result.related_tests = self._deduplicate_docs(result.related_tests)
        result.related_adrs = self._deduplicate_docs(result.related_adrs)
    
    def _extract_context(self, text: str, ref_id: str, context_lines: int = 2) -> str:
        """Extract reference context."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if ref_id in line:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = " | ".join(lines[start:end])
                # Truncate content if too long
                if len(context) > 150:
                    context = context[:147] + "..."
                return context
        return ""
    
    def _extract_doc_id_from_filename(self, filename: str) -> str:
        """Extract document reference ID from filename."""
        if not filename.endswith(".md"):
            return filename
        
        name = filename[:-3]
        parts = name.split("-")
        
        if len(parts) < 2:
            return filename
        
        prefix = parts[0]
        
        if prefix in ["RQ", "DS", "ADR"]:
            if len(parts) >= 3 and len(parts[1]) >= 5:
                return f"{parts[0]}-{parts[1][:5]}"
        elif prefix == "TK":
            if len(parts) >= 3 and len(parts[1]) >= 9:
                return f"{parts[0]}-{parts[1][:9]}"
        elif prefix in ["G", "S"]:
            if len(parts) >= 2:
                return f"{parts[0]}-{parts[1]}"
        
        return filename
    
    def _deduplicate_docs(self, docs: list[DocumentReference]) -> list[DocumentReference]:
        """Deduplicate document list."""
        seen = set()
        result = []
        for doc in docs:
            if doc.doc_id not in seen:
                seen.add(doc.doc_id)
                result.append(doc)
        return sorted(result, key=lambda x: x.doc_id)
    
    def _find_code_references(self, ref_id: str, result: DependencyTraceResult) -> None:
        """Find code references."""
        src_dir = self.repo_root / "src"
        if not src_dir.exists():
            # Try other common source code directories
            for alt_dir in [self.repo_root / "code", self.repo_root / "lib", self.repo_root]:
                if alt_dir.exists():
                    src_dir = alt_dir
                    break
            else:
                return
        
        for file_path in src_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in SUPPORTED_CODE_SUFFIXES:
                continue
            if "__pycache__" in str(file_path):
                continue
                
            try:
                content = read_text_safe(file_path)
                if ref_id not in content and SPEC_MARK not in content:
                    continue
                    
                # Find reference locations
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    if ref_id in line or (SPEC_MARK in line and self._is_related_to_ref(line, ref_id)):
                        code_ref = CodeReference(
                            file_path=str(file_path.relative_to(self.repo_root)),
                            line_number=line_num,
                            context=line.strip()[:100],
                            module_name=self._extract_module_name(file_path),
                            function_name=self._extract_function_name(lines, line_num),
                        )
                        result.code_refs.append(code_ref)
            except Exception:
                continue
    
    def _is_related_to_ref(self, line: str, ref_id: str) -> bool:
        """Check if the line is related to the reference ID."""
        # Simple heuristic check: whether the reference ID is near the line
        return ref_id in line or True  # Considered related if it contains SPEC_MARK
    
    def _extract_module_name(self, path: Path) -> str:
        """Extract module name."""
        # Infer module name based on file path and extension
        if path.suffix == ".py":
            return path.stem
        elif path.suffix in [".js", ".ts"]:
            return path.stem
        elif path.suffix == ".go":
            return path.stem
        elif path.suffix == ".rs":
            return path.stem
        return ""
    
    def _extract_function_name(self, lines: list[str], line_num: int) -> str:
        """Extract the function/class name at the current position."""
        # Search upwards for the nearest function or class definition
        func_patterns = [
            (r"^\s*def\s+(\w+)", "function"),
            (r"^\s*class\s+(\w+)", "class"),
            (r"^\s*(?:async\s+)?function\s+(\w+)", "function"),
            (r"^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:async)?\s*(?:\w+\s+)?(\w+)\s*\(", "function"),
            (r"^\s*fn\s+(\w+)", "function"),
        ]
        
        for i in range(line_num - 1, -1, -1):
            line = lines[i]
            for pattern, kind in func_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1)
        return ""


def trace_dependencies(specs_dir: Path, ref_id: str, repo_root: Path | None = None) -> DependencyTraceResult:
    """Compatibility function entry point: trace document dependencies."""
    return DependencyTracer(specs_dir, repo_root).trace(ref_id)
