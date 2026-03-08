"""
Dependency governance checker, identifying high-risk and non-reproducible dependency declarations.

## Specification References

This checker implements the validation logic for the following specifications:

| Specification Document | Reference ID | Applicable Section |
|------------------------|--------------|--------------------|
| Trusted Compliance     | S08          | Dependency Admission |
| Coding Standards       | S02          | Dependencies and Reuse |

### S08-Trusted Compliance Requirements
- Third-party dependencies must pass admission audit.
- Prohibit using dependencies with unpinned versions.
- Lock files must exist to ensure reproducibility.

### S02-Coding Standards Requirements
- Prohibit copy-pasting code from unknown sources.
- Third-party dependency admission, licensing, SBOM, and supply chain control.

## Implementation Mapping

| Method | Spec Requirement | Spec Section |
|--------|------------------|--------------|
| `is_risky_spec()` | High-risk version identification | S08-Dependency Admission |
| `is_unpinned_spec()` | Range version detection | S08-Reproducibility |
| `check_lockfile_presence()` | Lock file presence | S08-Supply Chain Control |
| `check_package_json()` | NPM dependency check | S08-Dependency List |
| `check_requirements_txt()` | Python dependency check | S08-Dependency List |

See also:
- specs/standards/S08-Trusted-Compliance.md
- specs/standards/S02-Coding-Standards.md
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error, log_info, log_warning

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

# ============================================================================
# High-risk Version Patterns
# ============================================================================
# Spec Ref: S08-Dependency Admission
# Note: The following version declaration methods are considered high-risk and are prohibited
RISKY_VERSION_PATTERNS = ["*", "latest"]

# Range version characters (non-exact fix)
RANGE_CHARS = set("^~><=*xX")

# Maximum nesting depth for requirements include
MAX_REQUIREMENT_INCLUDE_DEPTH = 10

ManifestParseErrors = tuple[type[Exception], ...]


def _build_manifest_parse_errors() -> ManifestParseErrors:
    """Build a set of dependency manifest parsing exceptions."""
    errors: ManifestParseErrors = (
        json.JSONDecodeError,
        ValueError,
        OSError,
        UnicodeDecodeError,
    )
    if tomllib is None:
        return errors
    return (*errors, tomllib.TOMLDecodeError)


MANIFEST_PARSE_ERRORS: ManifestParseErrors = _build_manifest_parse_errors()


class DependencyChecker:
    """
    Execute dependency manifest risk and reproducibility checks for multiple languages.

    Spec Ref:
    - S08 Trusted Compliance: Dependency admission, supply chain control
    - S02 Coding Standards: Third-party dependency admission

    Supported package managers:
    - NPM: package.json
    - Python: requirements.txt, pyproject.toml
    - Rust: Cargo.toml
    - Go: go.mod

    Check Rules:
    1. High-risk versions: `*`, `latest`, git+http, and other direct references.
    2. Range versions: `^`, `~`, `>`, `<`, `*`, `x`, and other non-exact fixes.
    3. Missing lock files: manifest exists but lock file does not.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize the dependency checker.

        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root

    @staticmethod
    def is_risky_spec(spec: str) -> bool:
        """
        Determine if the version declaration belongs to a high-risk source or a floating label.

        Spec Ref: S08-Dependency Admission

        High-risk types:
        - `*` or `latest`: Floating versions
        - `git+`: Direct Git references
        - `http://` or `https://`: Remote URLs
        - `file:` or `path:`: Local paths

        Args:
            spec: Version declaration string

        Returns:
            bool: True indicates high risk
        """
        lowered = spec.strip().lower()
        if lowered in RISKY_VERSION_PATTERNS:
            return True
        if lowered.startswith(("git+", "http://", "https://", "file:", "path:")):
            return True
        return False

    @staticmethod
    def is_unpinned_spec(spec: str) -> bool:
        """Determine if the version declaration is a range constraint rather than an exact fixed version."""
        normalized = spec.strip()
        if not normalized:
            return False
        if DependencyChecker.is_risky_spec(normalized):
            return False
        return any(ch in RANGE_CHARS for ch in normalized)

    @staticmethod
    def check_package_json(path: Path, warnings: list[str], errors: list[str]) -> None:
        """Check version declaration risks in various dependency sections of package.json."""
        data = json.loads(read_text_safe(path))
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            deps = data.get(section, {})
            if not isinstance(deps, dict):
                continue
            for name, spec in deps.items():
                spec_text = str(spec)
                if DependencyChecker.is_risky_spec(spec_text):
                    errors.append(f"{path}: {section}.{name} uses high-risk version declaration {spec_text}")
                elif DependencyChecker.is_unpinned_spec(spec_text):
                    warnings.append(f"{path}: {section}.{name} uses range version {spec_text}")

    @staticmethod
    def extract_requirement_include_target(line: str) -> str:
        """Extract the included file path from a requirements include statement."""
        stripped = line.strip()
        if stripped.startswith("-r") and len(stripped) > 2 and not stripped[2].isspace():
            return stripped[2:].strip()
        if stripped.startswith("--requirement="):
            return stripped.split("=", 1)[1].strip()

        parts = shlex.split(stripped)
        if len(parts) >= 2 and parts[0] in {"-r", "--requirement"}:
            return parts[1].strip()
        return ""

    @staticmethod
    def iterate_requirement_entries(
        path: Path,
        warnings: list[str],
        visited: set[Path],
        depth: int = 0,
    ) -> list[tuple[Path, int, str]]:
        """Recursively expand requirements include and return valid dependency entries."""
        if depth > MAX_REQUIREMENT_INCLUDE_DEPTH:
            warnings.append(f"{path}: include nesting exceeds maximum depth {MAX_REQUIREMENT_INCLUDE_DEPTH}")
            return []

        normalized = path.resolve()
        if normalized in visited:
            warnings.append(f"{path}: Detected circular reference in requirements include, skipped")
            return []
        if not path.exists():
            warnings.append(f"{path}: requirements include file does not exist, skipped")
            return []

        visited.add(normalized)
        entries: list[tuple[Path, int, str]] = []
        for idx, raw in enumerate(read_text_safe(path).splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith(("-r", "--requirement")):
                target = DependencyChecker.extract_requirement_include_target(line)
                if not target:
                    warnings.append(f"{path}:{idx} unable to parse requirement include syntax: {line}")
                    continue
                include_path = (path.parent / target).resolve()
                entries.extend(DependencyChecker.iterate_requirement_entries(include_path, warnings, visited, depth + 1))
                continue

            if line.startswith(("-c", "--constraint")):
                continue
            entries.append((path, idx, line))
        return entries

    @staticmethod
    def check_requirements_txt(path: Path, warnings: list[str], errors: list[str]) -> None:
        """Check requirements.txt for direct references and unpinned versions."""
        entries = DependencyChecker.iterate_requirement_entries(path, warnings, visited=set())
        for source_path, idx, line in entries:
            if " @ " in line:
                errors.append(f"{source_path}:{idx} uses direct reference dependency {line}")
                continue

            if "==" in line:
                continue
            if re.search(r"[<>~!]", line):
                warnings.append(f"{source_path}:{idx} uses range version {line}")
            else:
                warnings.append(f"{source_path}:{idx} version not explicitly pinned {line}")

    @staticmethod
    def check_pyproject(path: Path, warnings: list[str], errors: list[str]) -> None:
        """Check declaration risks in project.dependencies of pyproject.toml."""
        if tomllib is None:
            warnings.append(f"{path}: Unable to parse pyproject.toml (current Python does not support tomllib)")
            return

        data = tomllib.loads(read_text_safe(path))
        project = data.get("project", {})
        deps = project.get("dependencies", []) if isinstance(project, dict) else []
        if isinstance(deps, list):
            for dep in deps:
                spec = str(dep)
                if DependencyChecker.is_risky_spec(spec):
                    errors.append(f"{path}: project.dependencies uses high-risk declaration {spec}")
                elif DependencyChecker.is_unpinned_spec(spec):
                    warnings.append(f"{path}: project.dependencies uses range declaration {spec}")

    @staticmethod
    def check_cargo_dependency_section(
        path: Path,
        section_name: str,
        deps: object,
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Check version and source risks for a single Cargo dependency section."""
        if not isinstance(deps, dict):
            return

        for name, spec in deps.items():
            version = ""
            if isinstance(spec, str):
                version = spec
            elif isinstance(spec, dict):
                if spec.get("workspace") is True:
                    continue
                version = str(spec.get("version", ""))
                if "path" in spec or "git" in spec:
                    errors.append(f"{path}: {section_name}.{name} uses path/git dependency")
                    continue

            if DependencyChecker.is_risky_spec(version):
                errors.append(f"{path}: {section_name}.{name} uses high-risk version declaration {version}")
            elif DependencyChecker.is_unpinned_spec(version):
                warnings.append(f"{path}: {section_name}.{name} uses range version {version}")

    @staticmethod
    def check_cargo_toml(path: Path, warnings: list[str], errors: list[str]) -> None:
        """Check dependency declarations in Cargo.toml (including target scopes)."""
        if tomllib is None:
            warnings.append(f"{path}: Unable to parse Cargo.toml (current Python does not support tomllib)")
            return

        data = tomllib.loads(read_text_safe(path))
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            DependencyChecker.check_cargo_dependency_section(path, section, data.get(section, {}), warnings, errors)

        target_map = data.get("target", {})
        if isinstance(target_map, dict):
            for target_name, target_table in target_map.items():
                if not isinstance(target_table, dict):
                    continue
                for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                    scoped = target_table.get(section, {})
                    scoped_name = f"target.{target_name}.{section}"
                    DependencyChecker.check_cargo_dependency_section(path, scoped_name, scoped, warnings, errors)

    @staticmethod
    def check_go_mod(path: Path, warnings: list[str], errors: list[str]) -> None:
        """Check latest and replace reproducibility risks in go.mod."""
        text = read_text_safe(path)
        in_require_block = False
        in_replace_block = False

        def check_replace_target(idx: int, line: str) -> None:
            """Check if the go.mod replace target introduces local or non-reproducible risks."""
            warnings.append(f"{path}:{idx} uses replace directive, please confirm reproducibility")
            if "=>" not in line:
                return
            right = line.split("=>", 1)[1].strip()
            if not right:
                return
            target = right.split()[0]
            if re.match(r"^(?:\.\.?/|/|[A-Za-z]:[/\\])", target):
                warnings.append(f"{path}:{idx} replace points to a local path, which may affect reproducibility")

        for idx, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue

            if line == "replace (":
                in_replace_block = True
                continue
            if in_replace_block and line == ")":
                in_replace_block = False
                continue

            if line.startswith("replace "):
                check_replace_target(idx, line)
                continue
            if in_replace_block:
                check_replace_target(idx, line)
                continue

            if line == "require (":
                in_require_block = True
                continue
            if in_require_block and line == ")":
                in_require_block = False
                continue

            if line.startswith("require ") and " latest" in line:
                errors.append(f"{path}:{idx} uses latest version")
            elif in_require_block and line.endswith(" latest"):
                errors.append(f"{path}:{idx} uses latest version")

    @staticmethod
    def check_lockfile_presence(repo_root: Path, existing_names: set[str], warnings: list[str]) -> None:
        """Check if the corresponding language lock file is missing based on existing manifests."""
        if "package.json" in existing_names:
            js_locks = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
            if not any((repo_root / lock_name).exists() for lock_name in js_locks):
                warnings.append("package.json exists but no lock file found (package-lock.json/pnpm-lock.yaml/yarn.lock)")

        if "Cargo.toml" in existing_names and not (repo_root / "Cargo.lock").exists():
            warnings.append("Cargo.toml exists but missing Cargo.lock")

        if "go.mod" in existing_names and not (repo_root / "go.sum").exists():
            warnings.append("go.mod exists but missing go.sum")

        if "pyproject.toml" in existing_names:
            python_locks = ("poetry.lock", "Pipfile.lock", "uv.lock", "requirements.lock")
            if not any((repo_root / lock_name).exists() for lock_name in python_locks):
                warnings.append("pyproject.toml exists but no common lock file found (poetry.lock/Pipfile.lock/uv.lock)")

    def running(self) -> int:
        """Execute the dependency check."""
        manifests = [
            self.repo_root / "package.json",
            self.repo_root / "requirements.txt",
            self.repo_root / "pyproject.toml",
            self.repo_root / "Cargo.toml",
            self.repo_root / "go.mod",
        ]
        existing = [path for path in manifests if path.exists()]
        if not existing:
            log_info("No dependency manifest files found, skipping dependency check")
            return 0

        warnings: list[str] = []
        errors: list[str] = []
        for manifest in existing:
            try:
                if manifest.name == "package.json":
                    self.check_package_json(manifest, warnings, errors)
                elif manifest.name == "requirements.txt":
                    self.check_requirements_txt(manifest, warnings, errors)
                elif manifest.name == "pyproject.toml":
                    self.check_pyproject(manifest, warnings, errors)
                elif manifest.name == "Cargo.toml":
                    self.check_cargo_toml(manifest, warnings, errors)
                elif manifest.name == "go.mod":
                    self.check_go_mod(manifest, warnings, errors)
            except MANIFEST_PARSE_ERRORS as exc:
                errors.append(f"{manifest}: parsing failed {exc}")

        existing_names = {manifest.name for manifest in existing}
        self.check_lockfile_presence(self.repo_root, existing_names, warnings)

        if warnings:
            log_warning("Dependency check warnings:")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("Dependency check failed:")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("Dependency check passed")
        return 0


def _is_risky_spec(spec: str) -> bool:
    """Compatibility function entry point: determine high-risk version declaration."""
    return DependencyChecker.is_risky_spec(spec)


def _is_unpinned_spec(spec: str) -> bool:
    """Compatibility function entry point: determine range version declaration."""
    return DependencyChecker.is_unpinned_spec(spec)


def _check_package_json(path: Path, warnings: list[str], errors: list[str]) -> None:
    """Compatibility function entry point: check package.json."""
    DependencyChecker.check_package_json(path, warnings, errors)


def _extract_requirement_include_target(line: str) -> str:
    """Compatibility function entry point: extract requirements include target."""
    return DependencyChecker.extract_requirement_include_target(line)


def _iterate_requirement_entries(
    path: Path,
    warnings: list[str],
    visited: set[Path],
    depth: int = 0,
) -> list[tuple[Path, int, str]]:
    """Compatibility function entry point: recursively expand requirements include."""
    return DependencyChecker.iterate_requirement_entries(path, warnings, visited, depth)


def _check_requirements_txt(path: Path, warnings: list[str], errors: list[str]) -> None:
    """Compatibility function entry point: check requirements.txt."""
    DependencyChecker.check_requirements_txt(path, warnings, errors)


def _check_pyproject(path: Path, warnings: list[str], errors: list[str]) -> None:
    """Compatibility function entry point: check pyproject.toml."""
    DependencyChecker.check_pyproject(path, warnings, errors)


def _check_cargo_dependency_section(
    path: Path,
    section_name: str,
    deps: object,
    warnings: list[str],
    errors: list[str],
) -> None:
    """Compatibility function entry point: check Cargo dependency section."""
    DependencyChecker.check_cargo_dependency_section(path, section_name, deps, warnings, errors)


def _check_cargo_toml(path: Path, warnings: list[str], errors: list[str]) -> None:
    """Compatibility function entry point: check Cargo.toml."""
    DependencyChecker.check_cargo_toml(path, warnings, errors)


def _check_go_mod(path: Path, warnings: list[str], errors: list[str]) -> None:
    """Compatibility function entry point: check go.mod."""
    DependencyChecker.check_go_mod(path, warnings, errors)


def _check_lockfile_presence(repo_root: Path, existing_names: set[str], warnings: list[str]) -> None:
    """Compatibility function entry point: check lock file presence."""
    DependencyChecker.check_lockfile_presence(repo_root, existing_names, warnings)


def check_dependencies(repo_root: Path) -> int:
    """Compatibility function entry point: execute dependency check."""
    return DependencyChecker(repo_root).running()
