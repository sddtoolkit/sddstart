"""
规范合规校验器，检查必需文档是否存在且非空。

## 规范引用

本校验器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 治理与流程 | G01 | 项目基线 |
| 质量保证 | S04 | 完整性检查 |

### G01-治理与流程 要求
- 项目必须有完整的规范目录结构
- 必需文档必须存在且非空

### S04-质量保证 要求
- 交付前必须验证必需文件存在性
- 空文件视为不符合规范

## 实现映射

| 类/方法 | 规范要求 | 规范章节 |
|---------|----------|----------|
| `SpecComplianceValidator` | 规范合规检查器 | G01-项目基线 |
| `running()` | 执行必需文件检查 | S04-完整性检查 |

参见：
- specs/govs/G01-治理与流程.md
- specs/standards/S04-质量保证.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_error, log_info


class SpecComplianceValidator:
    """
    校验必需规范文件的存在性与非空性。

    规范引用：
    - G01 治理与流程：项目基线
    - S04 质量保证：完整性检查

    功能：
    1. 检查指定文件是否存在
    2. 检查文件是否非空
    3. 报告所有缺失或空文件
    """

    def __init__(self, specs_dir: Path, required_rel_paths: list[str]) -> None:
        """初始化规范合规检查器。"""
        self.specs_dir = specs_dir
        self.required_rel_paths = required_rel_paths

    def running(self) -> int:
        """执行必需文件检查。"""
        missing = 0
        for rel in self.required_rel_paths:
            path = self.specs_dir / rel
            if not path.exists() or path.stat().st_size == 0:
                log_error(f"缺失或为空：{path}")
                missing = 1
        if missing:
            return 1
        log_info("完整性检查通过")
        return 0


def check_required_files(specs_dir: Path, required_rel_paths: list[str]) -> int:
    """兼容函数入口：校验必需规范文件。"""
    return SpecComplianceValidator(specs_dir, required_rel_paths).running()
