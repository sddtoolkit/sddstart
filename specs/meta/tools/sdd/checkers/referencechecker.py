"""
Document reference relationship manager, providing reference query, update, delete, and index maintenance functions.

## Specification References

This checker implements validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Sections |
|------------------------|--------------|---------------------|
| Document Coding Specification | S01 | Reference ID Rules |
| Quality Assurance | S04 | Traceability Integrity |
| Evidence Specification | S06 | Evidence Association |

### S01 Document Coding Specification Requirements
- Reference IDs are used for cross-referencing between documents.
- Reference IDs must be unique across the entire specs/ directory.

### S04 Quality Assurance Requirements
- Traceability links must be complete and verifiable.
- Missing associations should be reported as errors.

### S06 Evidence Specification Requirements
- Evidence must be associated with the corresponding task, change, or release record.
- Ensure traceability.

## Implementation Mapping

| Method | Specification Requirement | Specification Section |
|--------|---------------------------|-----------------------|
| `CCC_DOC_PATTERN` | CCC document path matching | S01-3.x |
| `REF_ID_PATTERNS` | Reference ID extraction patterns | S01-2.1 |
| `extract_ref_id_from_filename()` | Reference ID extraction | S01-2.1 |
| `build_reference_index()` | Build reference index | S04 Traceability Management |
| `check_orphaned_references()` | Orphaned reference check | S06 Evidence Association |

See also:
- specs/standards/S01-文档编码规范.md
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional


@dataclass
class Reference:
    """
    Reference relationship data class.

    Specification Reference: S01-2.1 Reference ID Definition, S06 Evidence Association

    Attributes:
        source_file: Source file path (relative to specs)
        source_ref_id: Source file reference ID (e.g., G01, S01, RQ-10102)
        target_file: Target file path (relative to specs)
        target_ref_id: Target file reference ID
        line_number: Line number where the reference is located
        context: Reference context (full line content)
        ref_type: Reference type (doc/index/code)
    """
    source_file: str  # Source file path (relative to specs)
    source_ref_id: str  # Source file reference ID (e.g., G01, S01, RQ-10102)
    target_file: str  # Target file path (relative to specs)
    target_ref_id: str  # Target file reference ID
    line_number: int  # Line number where the reference is located
    context: str  # Reference context (full line content)
    ref_type: str  # Reference type: doc (document), index (index), code (code)


class ReferenceManager:
    """
    Document reference relationship manager.

    Specification References:
    - S01 Document Coding Specification: Reference ID Rules
    - S04 Quality Assurance: Traceability Integrity
    - S06 Evidence Specification: Evidence Association

    Functions:
    1. Scan and establish reference relationships between documents.
    2. Build forward/reverse reference indices.
    3. Check for orphaned references (referencing non-existent documents).
    4. Batch update reference IDs.
    5. Generate reference relationship reports.
    """

    # Spec Ref: S01-3.x - CCC encoded document path matching pattern
    CCC_DOC_PATTERN = re.compile(
        r'specs/([a-zA-Z0-9_\-]+)/(RQ-\d{5}|DS-\d{5}|TK-\d{9}|ADR-\d{5}|G\d{2}|S\d{2}|[^\s\'"`)]+\.(?:md|yaml))'
    )

    # Spec Ref: S01-2.1 - Reference ID extraction pattern
    REF_ID_PATTERNS = {
        'RQ': re.compile(r'RQ-(\d{3})(\d{2})'),
        'DS': re.compile(r'DS-(\d{3})(\d{2})'),
        'TK': re.compile(r'TK-(\d{3})(\d{4})(\d{2})'),
        'ADR': re.compile(r'ADR-(\d{3})(\d{2})'),
        'G': re.compile(r'G(\d{2})'),
        'S': re.compile(r'S(\d{2})'),
    }
    
    def __init__(self, specs_dir: str = "specs"):
        self.specs_dir = Path(specs_dir)
        self.index_path = self.specs_dir / "meta/index" / "reference-index.json"
        self.references: List[Reference] = []
        self._ref_id_cache: Dict[str, str] = {}  # Cache: file path -> reference ID
    
    def extract_ref_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract reference ID from filename."""
        if not filename.endswith('.md'):
            return None
        
        name = filename[:-3]  # Remove .md
        parts = name.split('-')
        
        if len(parts) < 1:
            return None
        
        prefix = parts[0]
        
        # RQ-10102-xxx -> RQ-10102
        if prefix in ['RQ', 'DS', 'ADR'] and len(parts) >= 2:
            return f"{prefix}-{parts[1]}"
        
        # TK-201260901-xxx -> TK-201260901
        if prefix == 'TK' and len(parts) >= 2:
            return f"{prefix}-{parts[1]}"
        
        # G01-xxx -> G01
        if prefix.startswith('G') and len(prefix) >= 3:
            return prefix
        
        # S01-xxx -> S01
        if prefix.startswith('S') and len(prefix) >= 3:
            return prefix
        
        return None
    
    def scan_all_references(self) -> List[Reference]:
        """
        Scan reference relationships in all documents.
        
        Returns:
            List of reference relationships.
        """
        self.references = []
        
        for root, _, files in os.walk(self.specs_dir):
            # Skip tools and cache directories
            if 'tools' in root or '__pycache__' in root:
                continue
            
            for file in files:
                if not (file.endswith('.md') or file.endswith('.py')):
                    continue
                
                source_path = Path(root) / file
                source_rel = source_path.relative_to(self.specs_dir)
                source_ref_id = self.extract_ref_id_from_filename(file)
                
                # Read file content
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except Exception:
                    continue
                
                # Scan each line for references
                for line_num, line in enumerate(lines, 1):
                    matches = self.CCC_DOC_PATTERN.finditer(line)
                    for match in matches:
                        target_rel = match.group(0)
                        target_file = target_rel.replace('specs/', '')
                        target_ref_id = self.extract_ref_id_from_filename(Path(target_file).name)
                        
                        # Determine reference type
                        if file.endswith('.py'):
                            ref_type = 'code'
                        elif 'meta/index' in str(source_rel):
                            ref_type = 'index'
                        else:
                            ref_type = 'doc'
                        
                        ref = Reference(
                            source_file=str(source_rel),
                            source_ref_id=source_ref_id or str(source_rel),
                            target_file=target_file,
                            target_ref_id=target_ref_id or target_file,
                            line_number=line_num,
                            context=line.strip(),
                            ref_type=ref_type
                        )
                        self.references.append(ref)
        
        return self.references
    
    def build_reference_index(self) -> Dict:
        """
        Build the reference index data structure.
        
        Returns:
            Index dictionary.
        """
        if not self.references:
            self.scan_all_references()
        
        # Forward index: document -> referenced documents
        forward_index: Dict[str, List[Dict]] = {}
        # Reverse index: document -> documents that reference it
        reverse_index: Dict[str, List[Dict]] = {}
        # Statistical information
        stats = {
            'total_references': len(self.references),
            'total_source_files': len(set(r.source_file for r in self.references)),
            'total_target_files': len(set(r.target_file for r in self.references)),
        }
        
        for ref in self.references:
            # Forward index
            if ref.source_file not in forward_index:
                forward_index[ref.source_file] = []
            forward_index[ref.source_file].append({
                'target_ref_id': ref.target_ref_id,
                'target_file': ref.target_file,
                'line_number': ref.line_number,
                'context': ref.context,
                'ref_type': ref.ref_type
            })
            
            # Reverse index
            if ref.target_file not in reverse_index:
                reverse_index[ref.target_file] = []
            reverse_index[ref.target_file].append({
                'source_ref_id': ref.source_ref_id,
                'source_file': ref.source_file,
                'line_number': ref.line_number,
                'context': ref.context,
                'ref_type': ref.ref_type
            })
        
        return {
            'version': '1.0',
            'stats': stats,
            'forward_index': forward_index,  # Who does the document reference?
            'reverse_index': reverse_index,  # Who references the document?
        }
    
    def save_index(self) -> None:
        """Save reference index to file."""
        index = self.build_reference_index()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def load_index(self) -> Dict:
        """Load reference index from file."""
        if not self.index_path.exists():
            return {}
        with open(self.index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def find_references_to(self, ref_id: str) -> List[Dict]:
        """
        Query which documents reference a specified document ID.
        
        Args:
            ref_id: Target document ID (e.g., G01, S01, RQ-10102).
        
        Returns:
            List of documents referencing this document.
        """
        index = self.load_index()
        reverse_index = index.get('reverse_index', {})
        
        results = []
        for target_file, refs in reverse_index.items():
            # target_file might be in 'govs/G04' or 'govs/G04-xxx.md' format.
            # Extract the last part from the path.
            target_name = Path(target_file).name
            
            # If target_name doesn't end with .md, it's an abbreviation (e.g., G04).
            # Use target_name directly as target_ref_id.
            if '.' not in target_name:
                target_ref_id = target_name
            else:
                # Full filename, extract reference ID.
                extracted = self.extract_ref_id_from_filename(target_name)
                target_ref_id = extracted if extracted else target_name
            
            if target_ref_id == ref_id:
                results.extend(refs)
        
        return results
    
    def find_references_from(self, ref_id: str) -> List[Dict]:
        """
        Query which documents are referenced by a specified document.
        
        Args:
            ref_id: Source document ID.
        
        Returns:
            List of documents referenced by this document.
        """
        index = self.load_index()
        forward_index = index.get('forward_index', {})
        
        results = []
        for source_file, refs in forward_index.items():
            source_ref_id = self.extract_ref_id_from_filename(Path(source_file).name)
            if source_ref_id == ref_id:
                results.extend(refs)
        
        return results
    
    def update_references(self, old_ref_id: str, new_ref_id: str, 
                         dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        Batch update reference relationships (replace old ID with new ID).
        
        Args:
            old_ref_id: Old reference ID.
            new_ref_id: New reference ID.
            dry_run: Whether to preview only without making changes.
        
        Returns:
            (Number of updates, Update log).
        """
        # First find the file corresponding to the new ID.
        new_file_pattern = None
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                current_ref_id = self.extract_ref_id_from_filename(file)
                if current_ref_id == new_ref_id:
                    new_file_pattern = f"specs/{Path(root).relative_to(self.specs_dir)}/{file}"
                    new_file_pattern = new_file_pattern.replace(str(self.specs_dir) + '/', '')
                    break
            if new_file_pattern:
                break
        
        if not new_file_pattern:
            return 0, [f"Error: file corresponding to reference ID {new_ref_id} not found"]
        
        # Find references to update.
        references_to_update = self.find_references_to(old_ref_id)
        
        if dry_run:
            log = [f"[Preview] Will update {len(references_to_update)} references:"]
            for ref in references_to_update:
                log.append(f"  - {ref['source_file']}:{ref['line_number']}")
            return len(references_to_update), log
        
        # Actual update.
        updated_count = 0
        log = []
        
        # Group by file.
        files_to_update: Dict[str, List[Tuple[int, str, str]]] = {}
        for ref in references_to_update:
            source_file = ref['source_file']
            if source_file not in files_to_update:
                files_to_update[source_file] = []
            files_to_update[source_file].append((
                ref['line_number'],
                ref['context'],
                ref['target_file']
            ))
        
        for source_file, refs in files_to_update.items():
            source_path = self.specs_dir / source_file
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, old_context, old_target in refs:
                    old_ref_pattern = f"specs/{old_target}"
                    new_ref_pattern = new_file_pattern
                    
                    if old_ref_pattern in lines[line_num - 1]:
                        lines[line_num - 1] = lines[line_num - 1].replace(
                            old_ref_pattern, new_ref_pattern
                        )
                        updated_count += 1
                        log.append(f"Updated: {source_file}:{line_num}")
                
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
            except Exception as e:
                log.append(f"Error: {source_file} - {e}")
        
        # Update index.
        if updated_count > 0:
            self.scan_all_references()
            self.save_index()
        
        return updated_count, log
    
    def delete_references_to(self, ref_id: str, dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        Delete all references to a specified document (mark references as outdated).
        
        Args:
            ref_id: Document ID for which references should be deleted.
            dry_run: Whether to preview only.
        
        Returns:
            (Number of deletions, log).
        """
        references_to_delete = self.find_references_to(ref_id)
        
        if dry_run:
            log = [f"[Preview] Will delete {len(references_to_delete)} references:"]
            for ref in references_to_delete:
                log.append(f"  - {ref['source_file']}:{ref['line_number']}")
            return len(references_to_delete), log
        
        # Actual deletion (mark as outdated).
        deleted_count = 0
        log = []
        
        files_to_update: Dict[str, List[Tuple[int, str]]] = {}
        for ref in references_to_delete:
            source_file = ref['source_file']
            if source_file not in files_to_update:
                files_to_update[source_file] = []
            files_to_update[source_file].append((ref['line_number'], ref['context']))
        
        for source_file, refs in files_to_update.items():
            source_path = self.specs_dir / source_file
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, context in refs:
                    # Add [Reference Outdated] marker to the end of the line.
                    if '[引用已过时]' not in lines[line_num - 1]:
                        lines[line_num - 1] = lines[line_num - 1].rstrip() + ' [引用已过时]\n'
                        deleted_count += 1
                        log.append(f"Marked as outdated: {source_file}:{line_num}")
                
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
            except Exception as e:
                log.append(f"Error: {source_file} - {e}")
        
        if deleted_count > 0:
            self.scan_all_references()
            self.save_index()
        
        return deleted_count, log
    
    def check_orphaned_references(self) -> List[Dict]:
        """
        Check for orphaned references (referencing non-existent documents).
        
        Returns:
            List of orphaned references.
        """
        orphaned = []
        
        # First establish mapping of all actual files (for lookup of abbreviated references).
        ref_id_to_file: Dict[str, str] = {}
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                if not file.endswith('.md'):
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.specs_dir)
                ref_id = self.extract_ref_id_from_filename(file)
                if ref_id:
                    ref_id_to_file[ref_id] = str(rel_path)
                    # Also store with directory prefix, e.g., govs/G01.
                    dir_prefix = str(rel_path.parent) if rel_path.parent != Path('.') else ''
                    if dir_prefix:
                        ref_id_to_file[f"{dir_prefix}/{ref_id}"] = str(rel_path)
        
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                if not (file.endswith('.md') or file.endswith('.py')):
                    continue
                
                source_path = Path(root) / file
                source_rel = source_path.relative_to(self.specs_dir)
                
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    continue
                
                matches = self.CCC_DOC_PATTERN.finditer(content)
                for match in matches:
                    target_rel = match.group(0).replace('specs/', '')
                    target_path = self.specs_dir / target_rel
                    
                    # Check if it exists (direct path or abbreviated mapping).
                    exists = target_path.exists()
                    if not exists:
                        # Try finding through ref_id mapping.
                        actual_file = ref_id_to_file.get(target_rel)
                        if actual_file:
                            exists = True
                    
                    if not exists:
                        # Extract line number.
                        pos = match.start()
                        line_num = content[:pos].count('\n') + 1
                        
                        orphaned.append({
                            'source_file': str(source_rel),
                            'target_file': target_rel,
                            'line_number': line_num,
                            'suggestion': f'Create file: {target_rel}'
                        })
        
        return orphaned
    
    def generate_reference_report(self) -> str:
        """Generate reference relationship report."""
        index = self.load_index()
        stats = index.get('stats', {})
        reverse_index = index.get('reverse_index', {})
        
        lines = [
            "# Document Reference Relationship Report",
            "",
            f"Generated at: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "## Statistics",
            "",
            f"- Total references: {stats.get('total_references', 0)}",
            f"- Total source files: {stats.get('total_source_files', 0)}",
            f"- Total target files: {stats.get('total_target_files', 0)}",
            "",
            "## Most Referenced Documents (Top 10)",
            "",
        ]
        
        # Count references.
        ref_counts = [(f, len(refs)) for f, refs in reverse_index.items()]
        ref_counts.sort(key=lambda x: x[1], reverse=True)
        
        for target_file, count in ref_counts[:10]:
            target_ref_id = self.extract_ref_id_from_filename(Path(target_file).name)
            lines.append(f"- `{target_file}` ({target_ref_id or 'N/A'}): {count} references")
        
        lines.extend([
            "",
            "## Orphaned Documents (Unreferenced Documents)",
            "",
        ])
        
        # Find all .md files.
        all_docs = set()
        referenced_docs = set(reverse_index.keys())
        
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.md'):
                    rel_path = Path(root).relative_to(self.specs_dir) / file
                    all_docs.add(str(rel_path))
        
        orphaned_docs = all_docs - referenced_docs
        
        if orphaned_docs:
            for doc in sorted(orphaned_docs):
                lines.append(f"- `{doc}`")
        else:
            lines.append("No unreferenced documents found.")
        
        return '\n'.join(lines)


# Compatibility function interfaces
def build_reference_index(specs_dir: str = "specs") -> Dict:
    """Build reference index."""
    manager = ReferenceManager(specs_dir)
    manager.scan_all_references()
    manager.save_index()
    return manager.build_reference_index()


def find_references_to(ref_id: str, specs_dir: str = "specs") -> List[Dict]:
    """Query which documents reference a specified ID."""
    manager = ReferenceManager(specs_dir)
    return manager.find_references_to(ref_id)


def find_references_from(ref_id: str, specs_dir: str = "specs") -> List[Dict]:
    """Query which documents are referenced by a specified document."""
    manager = ReferenceManager(specs_dir)
    return manager.find_references_from(ref_id)


def update_references(old_ref_id: str, new_ref_id: str, 
                     dry_run: bool = False, specs_dir: str = "specs") -> Tuple[int, List[str]]:
    """Batch update references."""
    manager = ReferenceManager(specs_dir)
    return manager.update_references(old_ref_id, new_ref_id, dry_run)


def delete_references_to(ref_id: str, dry_run: bool = False, 
                        specs_dir: str = "specs") -> Tuple[int, List[str]]:
    """Delete references."""
    manager = ReferenceManager(specs_dir)
    return manager.delete_references_to(ref_id, dry_run)


def check_orphaned_references(specs_dir: str = "specs") -> List[Dict]:
    """Check for orphaned references."""
    manager = ReferenceManager(specs_dir)
    return manager.check_orphaned_references()


def generate_reference_report(specs_dir: str = "specs") -> str:
    """Generate reference report."""
    manager = ReferenceManager(specs_dir)
    return manager.generate_reference_report()


if __name__ == "__main__":
    # Test
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        manager = ReferenceManager()
        
        if cmd == "build":
            manager.scan_all_references()
            manager.save_index()
            print(f"Reference index saved to: {manager.index_path}")
            
        elif cmd == "find-to" and len(sys.argv) > 2:
            refs = manager.find_references_to(sys.argv[2])
            print(f"Documents referencing {sys.argv[2]}:")
            for ref in refs:
                print(f"  - {ref['source_file']}:{ref['line_number']}")
                
        elif cmd == "find-from" and len(sys.argv) > 2:
            refs = manager.find_references_from(sys.argv[2])
            print(f"{sys.argv[2]} references:")
            for ref in refs:
                print(f"  - {ref['target_file']}")
                
        elif cmd == "report":
            print(manager.generate_reference_report())
            
        elif cmd == "orphaned":
            orphaned = manager.check_orphaned_references()
            print(f"Found {len(orphaned)} orphaned references:")
            for item in orphaned:
                print(f"  - {item['source_file']}:{item['line_number']} -> {item['target_file']}")
