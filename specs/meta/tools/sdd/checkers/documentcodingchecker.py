"""
Document coding specification checker.

[SDD Traceability]
- Standard: S01 (Document Coding Specification)

## Specification References

This checker implements validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Sections |
|------------------------|--------------|---------------------|
| Document Coding Specification | S01 | Full text |

### S01 Document Coding Specification Requirements
- Coding Composition: `<PREFIX>-<CODE_SEGMENT>-<SLUG>.md`
- Prefix Types: RQ (Requirement), DS (Design), TK (Task), ADR (Decision), G (Governance), S (Standard)
- Separator Specification: Unique separator `-`, underscores and spaces are prohibited
- NN Code Rules: 01-99 or AA-ZZ (excluding O, I, L)
- CCC Code Range: 100-999, divided by technical layers
- Exempt Files: README.md, INDEX.md, and main document files are not restricted by the specification

## Implementation Mapping

| Method | Specification Requirement | Specification Section |
|--------|---------------------------|-----------------------|
| `VALID_PREFIXES` | Six document prefix definitions | S01-1.2 Coding Composition |
| `CCC_RANGES` | CCC code classification ranges | S01-5.1 CCC Code |
| `_check_rq_ds_adr()` | RQ/DS/ADR format validation | S01-3.1~3.4 |
| `_check_tk()` | TK format validation (including YYWW) | S01-3.3 |
| `_check_gov_std()` | G/S format validation | S01-3.5~3.6 |
| `extract_reference_id()` | Reference ID extraction | S01-2.1 Reference ID Definition |

See also:
- specs/standards/S01-文档编码规范.md
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
from sdd.utils import resolve_spec_path


class DocumentCodingChecker:
    """
    Document coding specification checker.

    Specification Reference: S01 Document Coding Specification

    Functions:
    1. Validate the coding format of six document types (RQ/DS/TK/ADR/G/S)
    2. Check uniqueness of reference IDs
    3. Provide document localization and renaming functions
    4. Validate the effectiveness of CCC and NN codes

    Supported document types (S01-3.x):
    - RQ: Requirement document, format `RQ-<CCC><NN>-<SLUG>需求.md`
    - DS: Design document, format `DS-<CCC><NN>-<SLUG>设计.md`
    - TK: Task document, format `TK-<CCC><YYWW><NN>-<SLUG>任务.md`
    - ADR: Decision document, format `ADR-<CCC><NN>-<SLUG>决策.md`
    - G: Governance document, format `G<NN>-<SLUG>.md`
    - S: Standard document, format `S<NN>-<SLUG>.md`
    """

    # Spec Ref: S01-1.2 Coding Composition - Six document prefixes
    VALID_PREFIXES = ['RQ', 'DS', 'TK', 'ADR', 'G', 'S']

    # Spec Ref: S01-5.2 NN Code - Exclude confusing letters O, I, L
    EXCLUDED_LETTERS = {'O', 'I', 'L'}
    VALID_LETTERS = set('ABCDEFGHJKMNPQRSTUVWXYZ')  # 23 available letters

    # Spec Ref: S01-5.1 CCC Code Classification Table
    CCC_RANGES = {
        'core': (100, 199),        # Project Core Layer
        'frontend': (200, 299),    # Frontend Technical Layer
        'business': (300, 399),    # Business Domain Layer
        'backend': (400, 499),     # Backend Technical Layer
        'data': (500, 599),        # Data Layer
        'component': (600, 699),   # Component/Tool Layer
        'special': (700, 799),     # Special Technical Layer
        'reserved': (800, 899),    # Reserved for expansion
        'ops': (900, 999),         # Ops Support Layer
    }

    def __init__(self, specs_dir: str = "specs"):
        self.specs_dir = Path(specs_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def check_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all documents.

        Returns:
            (passed, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Collect all reference IDs for uniqueness validation
        ref_ids: dict[str, str] = {}

        for root, dirs, files in os.walk(self.specs_dir):
            # Skip tools and __pycache__ directories
            if 'tools' in root or '__pycache__' in root:
                continue

            for file in files:
                if not file.endswith('.md'):
                    continue

                filepath = Path(root) / file
                rel_path = filepath.relative_to(self.specs_dir)

                # Validate document coding
                is_valid, error = self._check_document(file, rel_path)

                if not is_valid:
                    self.errors.append(f"{rel_path}: {error}")
                    continue

                # Extract reference ID and check for uniqueness
                ref_id = self.extract_reference_id(file)
                if ref_id:
                    if ref_id in ref_ids:
                        self.errors.append(
                            f"{rel_path}: Duplicate reference ID '{ref_id}' "
                            f"(already exists in {ref_ids[ref_id]})"
                        )
                    else:
                        ref_ids[ref_id] = str(rel_path)

        return len(self.errors) == 0, self.errors, self.warnings

    def _check_document(self, filename: str, rel_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a single document.

        Returns:
            (passed, error_message)
        """
        # Exemptions: README.md and INDEX.md are not restricted by document coding specs
        if filename in ('README.md', 'INDEX.md'):
            return True, None

        # Main document exemptions: allow simplified naming for main documents in core directories
        # These are project baseline documents, no mandatory renaming
        main_doc_exceptions = {
            '1-reqs/requirements.md',
            '2-designs/architecture.md',
            '3-tasks/task-plan.md',
            'tests/test-plan.md',
            'releases/release-plan.md',
            'runbook/runbook.md',
            'changelogs/CHANGELOG.md',
        }
        str_path = str(rel_path)
        if str_path in main_doc_exceptions:
            return True, None

        # Parse filename first to determine if CCC coding system is used
        parts = filename.replace('.md', '').split('-')

        # Check for CCC coding prefix
        prefix = parts[0] if parts else ""

        # Special handling for G and S prefixes (e.g., G01, S01)
        # Extract prefix type: G01 -> G, S01 -> S, RQ-10102 -> RQ
        if prefix.startswith('G'):
            prefix_type = 'G'
        elif prefix.startswith('S'):
            prefix_type = 'S'
        else:
            prefix_type = prefix

        # Check if core directories must use specification naming
        strict_naming_dirs = {
            '1-reqs/': 'RQ',
            '2-designs/': 'DS',
            '3-tasks/': 'TK',
            'adrs/': 'ADR',
        }
        for dir_prefix, expected_doc_prefix in strict_naming_dirs.items():
            if str_path.startswith(dir_prefix):
                if prefix_type != expected_doc_prefix:
                    return False, f"Documents under directory '{dir_prefix}' must use '{expected_doc_prefix}' prefix, actually '{prefix}'"

        # Use traditional naming check if not one of the six document prefixes
        if prefix_type not in self.VALID_PREFIXES:
            return self._check_traditional_naming(filename)

        # Strict checks for documents using the CCC coding system
        # Check separator (only minus sign allowed)
        if '_' in filename:
            return False, "Contains underscore '_', only hyphens '-' are allowed"

        # Check for spaces
        if ' ' in filename:
            return False, "Contains spaces, which are not allowed"

        if len(parts) < 2:
            return False, "Format error, at least prefix and SLUG are required"

        # Specific validation based on prefix
        if prefix_type in ['RQ', 'DS', 'ADR']:
            return self._check_rq_ds_adr(filename, parts)
        elif prefix_type == 'TK':
            return self._check_tk(filename, parts)
        elif prefix_type in ['G', 'S']:
            return self._check_gov_std(filename, parts)

        return True, None

    def _check_traditional_naming(self, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate traditional naming (non-six document types: templates, examples, agents, skills, tools, etc.)."""
        # Special allowed files
        special_allowed = {
            'README.md', 'CHANGELOG.md', 'index.md', 'sources.md',
            'traceability.md', 'capability-matrix.md', 'agents.md',
            'skills.md', 'tools.md', 'user-guide.md', 'readme.md',
            'requirements.md', 'architecture.md', 'task-plan.md',
            'test-plan.md', 'release-plan.md', 'runbook.md',
        }

        name_without_ext = filename.replace('.md', '')
        if filename in special_allowed or name_without_ext in special_allowed:
            return True, None

        # Templates and examples use lowercase letters, numbers, hyphens, dots
        if re.match(r'^[a-z0-9\-\.]+\.md$', filename):
            # Check for prohibited non-semantic filenames
            banned_names = {'final', 'new', 'temp', 'tmp', 'draft'}
            if name_without_ext.lower() in banned_names:
                return False, f"Prohibited non-semantic filename '{filename}'"
            return True, None

        # Allow files containing README
        if 'README' in filename:
            return True, None

        return False, "Traditional naming only allows lowercase letters, numbers, hyphens, and dots"

    def _check_rq_ds_adr(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate RQ/DS/ADR format: <PREFIX>-<CCC><NN>-<SLUG><suffix>.md.
        Example: RQ-10102-用户注册需求.md
        """
        prefix = parts[0]

        # Check format: at least 3 segments (prefix - code - SLUG...)
        if len(parts) < 3:
            return False, f"Format error, should be {prefix}-<CCC><NN>-<SLUG><suffix>.md"

        # Check code segment
        code_segment = parts[1]
        if len(code_segment) < 5:
            return False, f"Code segment length error, should be at least 5 digits, actually {len(code_segment)}"

        # Extract CCC (first 3 digits)
        ccc_str = code_segment[:3]
        if not ccc_str.isdigit():
            return False, f"CCC code must be 3 digits, actually '{ccc_str}'"

        ccc = int(ccc_str)
        if not (100 <= ccc <= 999):
            return False, f"CCC code must be between 100-999, actually {ccc}"

        # Extract NN (4th-5th digits)
        nn_str = code_segment[3:5]
        if not self._is_valid_nn(nn_str):
            return False, f"NN code format error, should be 01-99 or AA-ZZ (excluding O, I, L), actually '{nn_str}'"

        # Check SLUG is not empty
        slug_parts = parts[2:]
        if not slug_parts or all(not p for p in slug_parts):
            return False, "SLUG cannot be empty"

        # Check suffix
        suffix_map = {'RQ': '需求', 'DS': '设计', 'ADR': '决策'}
        expected_suffix = suffix_map.get(prefix)
        if expected_suffix and not filename.endswith(f'{expected_suffix}.md'):
            return False, f"Suffix error, should end with '{expected_suffix}.md'"

        return True, None

    def _check_tk(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate TK format: TK-<CCC><YYWW><NN>-<SLUG>任务.md.
        Example: TK-201260901-前端页面开发任务.md
        """
        if len(parts) < 3:
            return False, "Format error, should be TK-<CCC><YYWW><NN>-<SLUG>任务.md"

        # Check code segment
        code_segment = parts[1]
        if len(code_segment) < 9:
            return False, f"Code segment length error, should be 9 digits, actually {len(code_segment)}"

        # Extract CCC (first 3 digits)
        ccc_str = code_segment[:3]
        if not ccc_str.isdigit():
            return False, f"CCC code must be 3 digits, actually '{ccc_str}'"

        ccc = int(ccc_str)
        if not (100 <= ccc <= 999):
            return False, f"CCC code must be between 100-999, actually {ccc}"

        # Extract YYWW (4th-7th digits)
        yyww_str = code_segment[3:7]
        if not yyww_str.isdigit():
            return False, f"YYWW code must be 4 digits, actually '{yyww_str}'"

        yy_val = int(yyww_str[:2])  # noqa: F841
        ww = int(yyww_str[2:])
        if not (1 <= ww <= 53):
            return False, f"Week number must be between 01-53, actually {ww}"

        # Extract NN (8th-9th digits)
        nn_str = code_segment[7:9]
        if not self._is_valid_nn(nn_str):
            return False, f"NN code format error, should be 01-99 or AA-ZZ (excluding O, I, L), actually '{nn_str}'"

        # Check suffix
        if not filename.endswith('任务.md'):
            return False, "Suffix error, should end with '任务.md'"

        return True, None

    def _check_gov_std(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate G/S format: <PREFIX><NN>-<SLUG>.md.
        Example: G01-项目宪章.md, S01-文档编码规范.md
        """
        # parts[0] contains prefix and NN, e.g., 'G01' or 'S01'
        prefix_with_nn = parts[0]

        # Extract prefix type and NN code
        if prefix_with_nn.startswith('G'):
            prefix_type = 'G'
            nn_str = prefix_with_nn[1:]  # G01 -> 01
        elif prefix_with_nn.startswith('S'):
            prefix_type = 'S'
            nn_str = prefix_with_nn[1:]  # S01 -> 01
        else:
            return False, f"Unknown prefix type: {prefix_with_nn}"

        # Check NN code
        if not nn_str:
            return False, f"Format error, {prefix_type} should be followed by NN code"

        if not self._is_valid_nn(nn_str):
            return False, f"NN code format error, should be 01-99 or AA-ZZ (excluding O, I, L), actually '{nn_str}'"

        # Check SLUG is not empty (parts[1] and beyond are SLUG)
        if len(parts) < 2:
            return False, f"Format error, should be {prefix_type}<NN>-<SLUG>.md"

        slug = '-'.join(parts[1:])
        if not slug:
            return False, "SLUG cannot be empty"

        # Check SLUG length (suggested 4-15 characters)
        if len(slug) > 30:
            self.warnings.append(f"SLUG too long ({len(slug)} characters), suggested to keep within 15 characters")

        return True, None

    def _is_valid_nn(self, nn_str: str) -> bool:
        """
        Check if NN code is valid.
        Format: 01-99 or AA-ZZ (excluding O, I, L)
        """
        if len(nn_str) != 2:
            return False

        # Numeric form
        if nn_str.isdigit():
            num = int(nn_str)
            return 1 <= num <= 99

        # Letter form
        if nn_str.isalpha() and nn_str.isupper():
            return all(c in self.VALID_LETTERS for c in nn_str)

        return False

    def extract_reference_id(self, filename: str) -> Optional[str]:
        """
        Extract reference ID from filename.

        Returns:
            Reference ID, or None if unable to extract.
        """
        if not filename.endswith('.md'):
            return None

        name = filename[:-3]  # Remove .md
        parts = name.split('-')

        if len(parts) < 2:
            return None

        prefix = parts[0]

        if prefix in ['RQ', 'DS', 'ADR']:
            # RQ-10102-用户注册需求 -> RQ-10102
            if len(parts) >= 3 and len(parts[1]) >= 5:
                return f"{parts[0]}-{parts[1][:5]}"
            return None
        elif prefix == 'TK':
            # TK-201260901-前端页面开发任务 -> TK-201260901
            if len(parts) >= 3 and len(parts[1]) >= 9:
                return f"{parts[0]}-{parts[1][:9]}"
            return None
        elif prefix in ['G', 'S']:
            # G01-项目宪章 -> G01
            # S01-文档编码规范 -> S01
            if len(parts) >= 2:
                # Need to handle the case where prefix and NN are together
                m = re.match(r'^([GS])([0-9A-Z]{2})', prefix)
                if m:
                    return f"{m.group(1)}{m.group(2)}"
            return None

        return None

    def locate_document(self, ref_id: str) -> Tuple[Optional[Path], Optional[str], List[Path]]:
        """Delegate document localization to unified implementation."""
        return resolve_spec_path(ref_id)

    def validate_ccc(self, ccc: int) -> Tuple[bool, str]:
        """
        Validate CCC code and return classification description.

        Returns:
            (is_valid, classification_description)
        """
        if not (100 <= ccc <= 999):
            return False, "CCC code must be between 100-999"

        for category, (start, end) in self.CCC_RANGES.items():
            if start <= ccc <= end:
                descriptions = {
                    'core': 'Project Core Layer',
                    'frontend': 'Frontend Technical Layer',
                    'business': 'Business Domain Layer',
                    'backend': 'Backend Technical Layer',
                    'data': 'Data Layer',
                    'component': 'Component/Tool Layer',
                    'special': 'Special Technical Layer',
                    'reserved': 'Reserved for expansion',
                    'ops': 'Ops Support Layer',
                }
                return True, descriptions.get(category, 'Unknown category')

        return False, "Unknown category"

    def suggest_nn(self, ccc: int, existing_docs: List[str]) -> str:
        """
        Suggest the next available NN code.

        Args:
            ccc: CCC classification code
            existing_docs: List of existing documents under this CCC

        Returns:
            Suggested NN code.
        """
        used_nns = set()

        for doc in existing_docs:
            ref_id = self.extract_reference_id(doc)
            if ref_id:
                # Extract NN part
                parts = ref_id.split('-')
                if len(parts) >= 2 and len(parts[1]) >= 5:
                    nn = parts[1][3:5] if parts[0] in ['RQ', 'DS', 'ADR'] else parts[1][7:9]
                    used_nns.add(nn)

        # Find the smallest available NN
        for i in range(1, 100):
            nn = f"{i:02d}"
            if nn not in used_nns:
                return nn

        # Digits exhausted, use letters
        for c1 in self.VALID_LETTERS:
            for c2 in self.VALID_LETTERS:
                nn = c1 + c2
                if nn not in used_nns:
                    return nn

        return "ZZ"  # Theoretically unreachable


def main():
    """Command line entry point."""
    import sys

    specs_dir = sys.argv[1] if len(sys.argv) > 1 else "specs"

    checker = DocumentCodingChecker(specs_dir)
    passed, errors, warnings = checker.check_all()

    print(f"\n{'='*60}")
    print("Document Coding Specification Check Results")
    print(f"{'='*60}")

    if passed and not errors:
        print("✅ All documents comply with coding specifications")
    else:
        print(f"❌ Found {len(errors)} errors")
        for error in errors:
            print(f"   - {error}")

    if warnings:
        print(f"\n⚠️ Found {len(warnings)} warnings")
        for warning in warnings:
            print(f"   - {warning}")

    print(f"{'='*60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    exit(main())
