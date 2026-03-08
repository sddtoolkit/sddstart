"""
生成需求到设计/任务/测试链路的追溯矩阵。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 质量保证 | S04 | 追溯完整性 |
| 证据规范 | S06 | 证据关联 |
| 交付控制 | S05 | 交付前检查 |

### S04-质量保证 要求
- 需求必须关联设计和测试
- 追溯链路必须完整且可验证
- 追溯矩阵必须自动化生成

### S06-证据规范 要求
- 证据必须关联到对应任务、变更或发布记录
- 追溯标识必须唯一且可解析

### S05-交付控制 要求
- 交付前必须验证追溯矩阵完整性
- 缺失链路必须作为错误报告

## 追溯标识格式

| 标识类型 | 格式 | 示例 |
|----------|------|------|
| REQ | req-xxx | req-user-auth |
| ADR | adr-xxx | adr-database-choice |
| DSN | dsn-xxx | dsn-api-gateway |
| TSK | tsk-xxx | tsk-impl-auth |
| TEST | test-xxx | test-login-flow |

## 实现映射

| 常量/类/方法 | 规范要求 | 规范章节 |
|---------------|----------|----------|
| `ID_PATTERNS` | 追溯标识正则模式 | S06-标识格式 |
| `TRACEABLE_DIRECTORIES` | 可追溯目录定义 | S04-追溯范围 |
| `TraceabilityGenerator` | 追溯矩阵生成器 | S04-追溯生成 |
| `build_traceability_matrix()` | 按REQ聚合关联 | S04-追溯聚合 |

参见：
- specs/standards/S04-质量保证.md
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

# 规范引用：S06-证据规范 - 追溯标识正则模式
ID_PATTERNS = {
    "reqs": re.compile(r"\breq-[a-z0-9-]+\b"),
    "adrs": re.compile(r"\badr-[a-z0-9-]+\b"),
    "designs": re.compile(r"\bdsn-[a-z0-9-]+\b"),
    "tasks": re.compile(r"\btsk-[a-z0-9-]+\b"),
    "tests": re.compile(r"\btest-[a-z0-9-]+\b"),
}

# 规范引用：S04-质量保证 - 可追溯目录定义
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
    生成追溯矩阵 JSON 与 Markdown 产物。

    规范引用：
    - S04 质量保证：追溯完整性
    - S06 证据规范：证据关联

    功能：
    1. 扫描可追溯目录中的所有文档
    2. 提取 REQ/ADR/DSN/TSK/TEST 标识
    3. 按 REQ 聚合关联关系
    4. 生成 JSON 和 Markdown 格式的追溯矩阵
    """

    def __init__(self, specs_dir: Path) -> None:
        """初始化追溯矩阵生成器。"""
        self.specs_dir = specs_dir

    @staticmethod
    def extract_identifiers(text: str, prefix: str) -> set[str]:
        """按前缀提取文档中的追溯标识，并过滤 gate 类型占位标识。"""
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
        """扫描可追溯目录并提取每个文档里的关系标识。"""
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
        """扫描代码目录，提取 Spec 引用标记。"""
        src_dir = REPO_ROOT / "src"
        implementations: dict[str, set[str]] = {}
        if not src_dir.is_dir():
            return implementations

        # 匹配 Spec: RQ-10101 等
        spec_mark_pattern = re.compile(r"Spec:\s*([A-Z]{1,4}-[A-Z0-9-]+)")

        for path in src_dir.rglob("*"):
            if not path.is_file() or path.suffix not in SUPPORTED_CODE_SUFFIXES:
                continue
            
            content = read_text_safe(path)
            found_ids = spec_mark_pattern.findall(content)
            
            rel_path = str(path.relative_to(REPO_ROOT))
            for ref_id in found_ids:
                # 归一化 ID
                prefix = ref_id.split("-")[0]
                norm_id = normalize_id(ref_id, prefix)
                implementations.setdefault(norm_id, set()).add(rel_path)
                
        return implementations

    def build_traceability_matrix(self) -> dict[str, dict[str, list[str]]]:
        """按 REQ 聚合 ADR/设计/任务/测试/代码实现引用关系。"""
        matrix: dict[str, dict[str, set[str]]] = {}
        
        # 1. 处理文档间的追溯
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

        # 2. 处理代码实现的追溯 (Code to RQ or Code to DS)
        code_refs = self.scan_code_implementations()
        
        # 将代码引用关联到对应的 RQ
        for ref_id, files in code_refs.items():
            if ref_id.startswith("RQ-") and ref_id in matrix:
                matrix[ref_id]["implementations"].update(files)
        
        # 如果代码引用 DS，则需要找到 DS 对应的 RQ
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
        """将追溯矩阵写入 JSON 文件。"""
        path = self.specs_dir / "meta/index/traceability.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def write_traceability_markdown(self, matrix: dict[str, dict[str, list[str]]]) -> Path:
        """将追溯矩阵写入可读的 Markdown 表格。"""
        path = self.specs_dir / "meta/index/traceability.md"
        lines = ["# 追踪矩阵", "", "| REQ | ADR | DSN | TSK | TEST | CODE |", "|---|---|---|---|---|---|"]
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
        """生成追溯矩阵的 JSON 与 Markdown 产物，并返回条目数。"""
        matrix = self.build_traceability_matrix()
        json_path = self.write_traceability_json(matrix)
        md_path = self.write_traceability_markdown(matrix)
        return json_path, md_path, len(matrix)



def generate_traceability_outputs(specs_dir: Path) -> tuple[Path, Path, int]:
    """生成追溯矩阵产物。"""
    return TraceabilityGenerator(specs_dir).running()

