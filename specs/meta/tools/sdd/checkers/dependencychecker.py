"""
依赖治理检查器，识别高风险与不可复现依赖声明。

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 可信合规 | S08 | 依赖准入 |
| 编码规范 | S02 | 依赖与复用 |

### S08-可信合规 要求
- 第三方依赖必须通过准入审核
- 禁止使用未固定版本的依赖
- 必须存在锁文件保证可复现性

### S02-编码规范 要求
- 禁止复制粘贴未知来源代码
- 第三方依赖准入、许可、SBOM 与供应链控制

## 实现映射

| 方法 | 规范要求 | 规范章节 |
|------|----------|----------|
| `is_risky_spec()` | 高风险版本识别 | S08-依赖准入 |
| `is_unpinned_spec()` | 范围版本检测 | S08-可复现性 |
| `check_lockfile_presence()` | 锁文件存在性 | S08-供应链控制 |
| `check_package_json()` | NPM 依赖检查 | S08-依赖清单 |
| `check_requirements_txt()` | Python 依赖检查 | S08-依赖清单 |

参见：
- specs/standards/S08-可信合规.md
- specs/standards/S02-编码规范.md
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
# 高风险版本模式
# ============================================================================
# 规范引用：S08-依赖准入
# 说明：以下版本声明方式被视为高风险，禁止使用
RISKY_VERSION_PATTERNS = ["*", "latest"]

# 范围版本字符（非精确固定）
RANGE_CHARS = set("^~><=*xX")

# requirements include 最大嵌套深度
MAX_REQUIREMENT_INCLUDE_DEPTH = 10

ManifestParseErrors = tuple[type[Exception], ...]


def _build_manifest_parse_errors() -> ManifestParseErrors:
    """构建依赖清单解析异常集合。"""
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
    执行多语言依赖清单风险与可复现性检查。

    规范引用：
    - S08 可信合规：依赖准入、供应链控制
    - S02 编码规范：第三方依赖准入

    支持的包管理器：
    - NPM: package.json
    - Python: requirements.txt, pyproject.toml
    - Rust: Cargo.toml
    - Go: go.mod

    检查规则：
    1. 高风险版本：`*`, `latest`, git+http 等直接引用
    2. 范围版本：`^`, `~`, `>`, `<`, `*`, `x` 等非精确固定
    3. 锁文件缺失：清单存在但锁文件不存在
    """

    def __init__(self, repo_root: Path) -> None:
        """
        初始化依赖检查器。

        Args:
            repo_root: 仓库根目录
        """
        self.repo_root = repo_root

    @staticmethod
    def is_risky_spec(spec: str) -> bool:
        """
        判断版本声明是否属于高风险来源或浮动标签。

        规范引用：S08-依赖准入

        高风险类型：
        - `*` 或 `latest`：浮动版本
        - `git+`：Git 直接引用
        - `http://` 或 `https://`：远程 URL
        - `file:` 或 `path:`：本地路径

        Args:
            spec: 版本声明字符串

        Returns:
            bool: True 表示高风险
        """
        lowered = spec.strip().lower()
        if lowered in RISKY_VERSION_PATTERNS:
            return True
        if lowered.startswith(("git+", "http://", "https://", "file:", "path:")):
            return True
        return False

    @staticmethod
    def is_unpinned_spec(spec: str) -> bool:
        """判断版本声明是否为范围约束而非精确固定版本。"""
        normalized = spec.strip()
        if not normalized:
            return False
        if DependencyChecker.is_risky_spec(normalized):
            return False
        return any(ch in RANGE_CHARS for ch in normalized)

    @staticmethod
    def check_package_json(path: Path, warnings: list[str], errors: list[str]) -> None:
        """检查 package.json 各依赖段的版本声明风险。"""
        data = json.loads(read_text_safe(path))
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            deps = data.get(section, {})
            if not isinstance(deps, dict):
                continue
            for name, spec in deps.items():
                spec_text = str(spec)
                if DependencyChecker.is_risky_spec(spec_text):
                    errors.append(f"{path}: {section}.{name} 使用高风险版本声明 {spec_text}")
                elif DependencyChecker.is_unpinned_spec(spec_text):
                    warnings.append(f"{path}: {section}.{name} 使用范围版本 {spec_text}")

    @staticmethod
    def extract_requirement_include_target(line: str) -> str:
        """从 requirements include 语句中提取被包含文件路径。"""
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
        """递归展开 requirements include，返回有效依赖条目。"""
        if depth > MAX_REQUIREMENT_INCLUDE_DEPTH:
            warnings.append(f"{path}: include 嵌套超过最大深度 {MAX_REQUIREMENT_INCLUDE_DEPTH}")
            return []

        normalized = path.resolve()
        if normalized in visited:
            warnings.append(f"{path}: 检测到 requirements include 循环引用，已跳过")
            return []
        if not path.exists():
            warnings.append(f"{path}: requirements include 文件不存在，已跳过")
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
                    warnings.append(f"{path}:{idx} requirement include 语法无法解析：{line}")
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
        """检查 requirements.txt 是否存在直接引用与未固定版本。"""
        entries = DependencyChecker.iterate_requirement_entries(path, warnings, visited=set())
        for source_path, idx, line in entries:
            if " @ " in line:
                errors.append(f"{source_path}:{idx} 使用直接引用依赖 {line}")
                continue

            if "==" in line:
                continue
            if re.search(r"[<>~!]", line):
                warnings.append(f"{source_path}:{idx} 使用范围版本 {line}")
            else:
                warnings.append(f"{source_path}:{idx} 未显式固定版本 {line}")

    @staticmethod
    def check_pyproject(path: Path, warnings: list[str], errors: list[str]) -> None:
        """检查 pyproject.toml 中 project.dependencies 的声明风险。"""
        if tomllib is None:
            warnings.append(f"{path}: 无法解析 pyproject.toml（当前 Python 不支持 tomllib）")
            return

        data = tomllib.loads(read_text_safe(path))
        project = data.get("project", {})
        deps = project.get("dependencies", []) if isinstance(project, dict) else []
        if isinstance(deps, list):
            for dep in deps:
                spec = str(dep)
                if DependencyChecker.is_risky_spec(spec):
                    errors.append(f"{path}: project.dependencies 使用高风险声明 {spec}")
                elif DependencyChecker.is_unpinned_spec(spec):
                    warnings.append(f"{path}: project.dependencies 使用范围声明 {spec}")

    @staticmethod
    def check_cargo_dependency_section(
        path: Path,
        section_name: str,
        deps: object,
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """检查单个 Cargo 依赖段的版本与来源风险。"""
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
                    errors.append(f"{path}: {section_name}.{name} 使用 path/git 依赖")
                    continue

            if DependencyChecker.is_risky_spec(version):
                errors.append(f"{path}: {section_name}.{name} 使用高风险版本声明 {version}")
            elif DependencyChecker.is_unpinned_spec(version):
                warnings.append(f"{path}: {section_name}.{name} 使用范围版本 {version}")

    @staticmethod
    def check_cargo_toml(path: Path, warnings: list[str], errors: list[str]) -> None:
        """检查 Cargo.toml（含 target 作用域）依赖声明。"""
        if tomllib is None:
            warnings.append(f"{path}: 无法解析 Cargo.toml（当前 Python 不支持 tomllib）")
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
        """检查 go.mod 中 latest 与 replace 可复现性风险。"""
        text = read_text_safe(path)
        in_require_block = False
        in_replace_block = False

        def check_replace_target(idx: int, line: str) -> None:
            """检查 go.mod replace 目标是否引入本地/不可复现风险。"""
            warnings.append(f"{path}:{idx} 使用 replace 指令，请确认可复现性")
            if "=>" not in line:
                return
            right = line.split("=>", 1)[1].strip()
            if not right:
                return
            target = right.split()[0]
            if re.match(r"^(?:\.\.?/|/|[A-Za-z]:[/\\])", target):
                warnings.append(f"{path}:{idx} replace 指向本地路径，可能影响可复现性")

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
                errors.append(f"{path}:{idx} 使用 latest 版本")
            elif in_require_block and line.endswith(" latest"):
                errors.append(f"{path}:{idx} 使用 latest 版本")

    @staticmethod
    def check_lockfile_presence(repo_root: Path, existing_names: set[str], warnings: list[str]) -> None:
        """根据已存在清单检查对应语言锁文件是否缺失。"""
        if "package.json" in existing_names:
            js_locks = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
            if not any((repo_root / lock_name).exists() for lock_name in js_locks):
                warnings.append("package.json 存在但未发现锁文件（package-lock.json/pnpm-lock.yaml/yarn.lock）")

        if "Cargo.toml" in existing_names and not (repo_root / "Cargo.lock").exists():
            warnings.append("Cargo.toml 存在但缺少 Cargo.lock")

        if "go.mod" in existing_names and not (repo_root / "go.sum").exists():
            warnings.append("go.mod 存在但缺少 go.sum")

        if "pyproject.toml" in existing_names:
            python_locks = ("poetry.lock", "Pipfile.lock", "uv.lock", "requirements.lock")
            if not any((repo_root / lock_name).exists() for lock_name in python_locks):
                warnings.append("pyproject.toml 存在但未发现常见锁文件（poetry.lock/Pipfile.lock/uv.lock）")

    def running(self) -> int:
        """执行依赖检查。"""
        manifests = [
            self.repo_root / "package.json",
            self.repo_root / "requirements.txt",
            self.repo_root / "pyproject.toml",
            self.repo_root / "Cargo.toml",
            self.repo_root / "go.mod",
        ]
        existing = [path for path in manifests if path.exists()]
        if not existing:
            log_info("未发现依赖清单文件，跳过依赖检查")
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
                errors.append(f"{manifest}: 解析失败 {exc}")

        existing_names = {manifest.name for manifest in existing}
        self.check_lockfile_presence(self.repo_root, existing_names, warnings)

        if warnings:
            log_warning("依赖检查告警：")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("依赖检查失败：")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("依赖检查通过")
        return 0


def _is_risky_spec(spec: str) -> bool:
    """兼容函数入口：判断高风险版本声明。"""
    return DependencyChecker.is_risky_spec(spec)


def _is_unpinned_spec(spec: str) -> bool:
    """兼容函数入口：判断范围版本声明。"""
    return DependencyChecker.is_unpinned_spec(spec)


def _check_package_json(path: Path, warnings: list[str], errors: list[str]) -> None:
    """兼容函数入口：检查 package.json。"""
    DependencyChecker.check_package_json(path, warnings, errors)


def _extract_requirement_include_target(line: str) -> str:
    """兼容函数入口：提取 requirements include 目标。"""
    return DependencyChecker.extract_requirement_include_target(line)


def _iterate_requirement_entries(
    path: Path,
    warnings: list[str],
    visited: set[Path],
    depth: int = 0,
) -> list[tuple[Path, int, str]]:
    """兼容函数入口：递归展开 requirements include。"""
    return DependencyChecker.iterate_requirement_entries(path, warnings, visited, depth)


def _check_requirements_txt(path: Path, warnings: list[str], errors: list[str]) -> None:
    """兼容函数入口：检查 requirements.txt。"""
    DependencyChecker.check_requirements_txt(path, warnings, errors)


def _check_pyproject(path: Path, warnings: list[str], errors: list[str]) -> None:
    """兼容函数入口：检查 pyproject.toml。"""
    DependencyChecker.check_pyproject(path, warnings, errors)


def _check_cargo_dependency_section(
    path: Path,
    section_name: str,
    deps: object,
    warnings: list[str],
    errors: list[str],
) -> None:
    """兼容函数入口：检查 Cargo 依赖段。"""
    DependencyChecker.check_cargo_dependency_section(path, section_name, deps, warnings, errors)


def _check_cargo_toml(path: Path, warnings: list[str], errors: list[str]) -> None:
    """兼容函数入口：检查 Cargo.toml。"""
    DependencyChecker.check_cargo_toml(path, warnings, errors)


def _check_go_mod(path: Path, warnings: list[str], errors: list[str]) -> None:
    """兼容函数入口：检查 go.mod。"""
    DependencyChecker.check_go_mod(path, warnings, errors)


def _check_lockfile_presence(repo_root: Path, existing_names: set[str], warnings: list[str]) -> None:
    """兼容函数入口：检查锁文件存在性。"""
    DependencyChecker.check_lockfile_presence(repo_root, existing_names, warnings)


def check_dependencies(repo_root: Path) -> int:
    """兼容函数入口：执行依赖检查。"""
    return DependencyChecker(repo_root).running()
