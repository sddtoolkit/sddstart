"""
变更日志检查器，校验日志文件存在且非空。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 版本号规范 | S10 | 变更记录 |
| 质量保证 | S04 | 变更追踪 |
| 证据规范 | S06 | 变更证据 |

### S10-版本号规范 要求
- 变更日志必须记录版本变更
- 变更日志格式必须符合约定

### S04-质量保证 要求
- 变更必须有日志记录
- 变更日志必须非空

### S06-证据规范 要求
- 变更记录作为证据必须存在
- 变更记录必须关联到具体变更

## 实现映射

| 类/方法 | 规范要求 | 规范章节 |
|---------|----------|----------|
| `ChangelogChecker` | 变更日志检查器 | S04-变更追踪 |
| `running()` | 执行变更日志检查 | S10-变更记录 |

参见：
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
- specs/standards/S10-版本号规范.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.io import check_file_integrity
from sdd.log import log_error, log_info


class ChangelogChecker:
    """
    检查变更日志文件有效性。

    规范引用：
    - S04 质量保证：变更追踪
    - S06 证据规范：变更证据
    - S10 版本号规范：变更记录

    功能：
    1. 检查变更日志文件是否存在
    2. 检查变更日志文件是否非空
    """

    def __init__(self, path: Path) -> None:
        """初始化变更日志检查器。"""
        self.path = path

    def running(self) -> int:
        """执行变更日志检查。"""
        ok, error_message = check_file_integrity(self.path, "变更日志")
        if not ok:
            log_error(error_message)
            return 1
        log_info("变更日志检查通过")
        return 0


def check_changelog_file(path: Path) -> int:
    """兼容函数入口：检查变更日志文件。"""
    return ChangelogChecker(path).running()
