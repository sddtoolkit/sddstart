"""
完整性检查器，验证追溯矩阵链路是否满足要求。

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 质量保证 | S04 | 追溯完整性 |
| 交付控制 | S05 | 交付前检查 |

### S04-质量保证 要求
- 需求必须关联设计和测试
- 追溯链路必须完整且可验证
- 缺失关联应作为错误报告

### S05-交付控制 要求
- 交付前必须通过完整性检查
- REQ 必须关联设计、任务、测试

## 实现映射

| 方法 | 规范要求 | 规范章节 |
|------|----------|----------|
| `REQUIRED_LINKS` | 必需的追溯链路 | S04-追溯完整性 |
| `_load_matrix()` | 加载追溯矩阵 | S04-追溯管理 |
| `running()` | 执行完整性校验 | S05-交付检查 |

参见：
- specs/standards/S04-质量保证.md
- specs/standards/S05-交付控制.md
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
    """追溯矩阵单个 REQ 条目的链路字段。"""

    adrs: list[object]
    designs: list[object]
    tasks: list[object]
    tests: list[object]


TraceabilityMatrix = dict[str, TraceabilityLinks | object]


class CompletenessChecker:
    """
    校验追溯矩阵中 REQ 链路完整性。

    规范引用：
    - S04 质量保证：追溯完整性要求
    - S05 交付控制：交付前检查

    检查规则：
    1. 每个 REQ 必须关联设计（designs）
    2. 每个 REQ 必须关联任务（tasks）
    3. 每个 REQ 必须关联测试（tests）
    4. ADR 关联为可选，缺失时仅警告

    追溯标识格式：
    - REQ: req-xxx
    - ADR: adr-xxx
    - DSN: dsn-xxx
    - TSK: tsk-xxx
    - TEST: test-xxx
    """

    # 追溯标识正则模式
    ID_PATTERNS = {
        "reqs": re.compile(r"\brq-[a-z0-9-]+\b"),
        "adrs": re.compile(r"\badr-[a-z0-9-]+\b"),
        "designs": re.compile(r"\bds-[a-z0-9-]+\b"),
        "tasks": re.compile(r"\btk-[a-z0-9-]+\b"),
        "tests": re.compile(r"\btest-[a-z0-9-]+\b"),
    }

    # 追溯标识对应目录映射
    DIRECTORY_BY_FIELD = {
        "reqs": "1-reqs",
        "adrs": "adrs",
        "designs": "2-designs",
        "tasks": "3-tasks",
        "tests": "tests",
    }

    # 规范引用：S04-追溯完整性 - REQ 必需的链路类型
    REQUIRED_LINKS = (
        ("designs", "设计"),
        ("tasks", "任务"),
        ("tests", "测试"),
        ("implementations", "代码实现"),
    )

    def __init__(self, specs_dir: Path) -> None:
        """初始化完整性检查器。"""
        self.specs_dir = specs_dir

    def _load_matrix(self) -> TraceabilityMatrix | None:
        """读取并解析追溯矩阵 JSON。"""
        trace_path = self.specs_dir / "meta/index/traceability.json"
        if not trace_path.exists():
            log_error("缺少 traceability.json，请先运行 generate-traceability-matrix")
            return None

        try:
            matrix = json.loads(read_text_safe(trace_path))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            log_error(f"追溯矩阵解析失败：{exc}")
            return None

        if not isinstance(matrix, dict):
            log_error("追溯矩阵格式错误：根节点必须为对象")
            return None
        return cast(TraceabilityMatrix, matrix)

    def _collecting_directory_identifiers(self, field: str) -> set[str]:
        """从目标目录提取并归一化指定类别的追溯标识。"""
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
        """收集各类别（REQ/ADR/DSN/TSK/TEST）已落盘标识集合。"""
        ids = {field: self._collecting_directory_identifiers(field) for field in self.DIRECTORY_BY_FIELD}
        # 代码实现没有对应的 specs 目录，我们假设在 traceability.json 中已记录即有效，
        # 具体的有效性由 TraceabilityGenerator 的扫描逻辑保证。
        ids["implementations"] = set() 
        return ids

    def running(self) -> int:
        """执行完整性检查。"""
        matrix = self._load_matrix()
        if matrix is None:
            return 1

        if not matrix:
            log_error("追溯矩阵为空：未发现可校验的 REQ 条目（req-*）")
            log_error("请先在需求/设计/任务/测试文档中建立 REQ/DSN/TSK/TEST 追溯标识")
            return 1

        warnings: list[str] = []
        errors: list[str] = []
        existing_identifiers = self._collecting_existing_identifiers()

        for req_id, links in sorted(matrix.items()):
            if not isinstance(links, dict):
                errors.append(f"{req_id} 的追溯结构错误（应为对象）")
                continue
            if req_id not in existing_identifiers["reqs"]:
                errors.append(f"{req_id} 在 1-reqs 中未找到对应定义")

            adrs = links.get("adrs", [])
            if not isinstance(adrs, list):
                errors.append(f"{req_id} 的 adrs 字段类型错误（应为列表）")
            elif not adrs:
                warnings.append(f"{req_id} 未关联 ADR")
            else:
                for adr_id in adrs:
                    if not isinstance(adr_id, str):
                        errors.append(f"{req_id} 的 adrs 包含非字符串条目")
                        continue
                    if adr_id not in existing_identifiers["adrs"]:
                        errors.append(f"{req_id} 关联的 ADR 不存在：{adr_id}")

            for field, label in self.REQUIRED_LINKS:
                items = links.get(field, [])
                if not isinstance(items, list):
                    errors.append(f"{req_id} 的 {field} 字段类型错误（应为列表）")
                elif not items:
                    errors.append(f"{req_id} 缺少{label}关联")
                else:
                    for linked_id in items:
                        if not isinstance(linked_id, str):
                            errors.append(f"{req_id} 的 {field} 包含非字符串条目")
                            continue
                        if field == "implementations":
                            # 代码实现文件不在 specs 目录下，不执行目录存在性检查
                            continue
                        if linked_id not in existing_identifiers[field]:
                            errors.append(f"{req_id} 关联的{label}不存在：{linked_id}")

        if warnings:
            log_warning("完整性检查告警：")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("完整性检查失败：")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("完整性检查通过")
        return 0


def check_completeness(specs_dir: Path) -> int:
    """兼容函数入口：执行追溯完整性检查。"""
    return CompletenessChecker(specs_dir).running()
