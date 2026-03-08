"""
规范漂移检查器，确保代码文件含有规范来源标记。

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 编码规范 | S02 | 审计与证据 |
| 证据规范 | S06 | 证据关联 |

### S02-编码规范 要求
- 必须保留执行证据（评审记录、报告、清单或日志）
- 证据必须关联到对应任务、变更或发布记录

### S06-证据规范 要求
- 代码实现必须可追溯到规范来源
- 漂移（代码与规范不一致）必须被检测和纠正

## 实现映射

| 方法 | 规范要求 | 规范章节 |
|------|----------|----------|
| `_collecting_missing_paths()` | 收集缺失标记的文件 | S06-证据关联 |
| `running()` | 执行漂移检查 | S02-审计证据 |

参见：
- specs/standards/S02-编码规范.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import re
from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error, log_info


class DriftChecker:
    """
    检查代码文件是否带有规范来源标记。

    规范引用：
    - S02 编码规范：审计与证据
    - S06 证据规范：证据关联

    功能：
    1. 扫描 src/ 目录下的代码文件
    2. 检查文件是否包含规范来源标记（如 `规范引用`、`Spec:` 等）
    3. 报告缺失标记的文件

    用途：
    - 防止代码与规范漂移
    - 确保代码实现可追溯到需求/设计
    """

    def __init__(self, repo_root: Path, supported_suffixes: set[str], spec_mark: str) -> None:
        """初始化漂移检查器。"""
        self.repo_root = repo_root
        self.supported_suffixes = supported_suffixes
        self.spec_mark = spec_mark

    def _collecting_missing_paths(self, src_dir: Path) -> list[str]:
        """收集缺少规范标记或引用无效 ID 的代码文件路径。"""
        issues: list[str] = []
        # 匹配 Spec: RQ-10101 或 Spec: RQ-10101 这种格式
        spec_pattern = re.compile(rf"{re.escape(self.spec_mark)}\s*([A-Z0-9-]+)")

        from sdd.utils import resolve_spec_path

        for path in src_dir.rglob("*"):
            if not path.is_file() or path.suffix not in self.supported_suffixes:
                continue
            content = read_text_safe(path)
            
            matches = spec_pattern.findall(content)
            if not matches:
                issues.append(f"缺失规范标记: {path}")
                continue
            
            for ref_id in matches:
                doc_path, error_msg, _ = resolve_spec_path(ref_id)
                if error_msg:
                    issues.append(f"无效引用 [{ref_id}]: {path} ({error_msg})")
                elif not doc_path:
                    issues.append(f"引用未找到 [{ref_id}]: {path}")
                    
        return issues

    def running(self) -> int:
        """执行漂移检查。"""
        src_dir = self.repo_root / "src"
        if not src_dir.is_dir():
            log_info("未发现 src/，跳过一致性检查")
            return 0

        issues = self._collecting_missing_paths(src_dir)
        if issues:
            log_error("规范一致性检查发现问题：")
            for item in issues:
                log_error(item)
            return 1

        log_info("一致性检查通过")
        return 0


def check_spec_drift(repo_root: Path, supported_suffixes: set[str], spec_mark: str) -> int:
    """兼容函数入口：执行代码漂移检查。"""
    return DriftChecker(repo_root, supported_suffixes, spec_mark).running()
