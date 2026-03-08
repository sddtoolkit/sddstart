"""
索引写入器，负责持久化索引文件内容。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 治理与流程 | G01 | 索引维护 |
| 质量保证 | S04 | 索引生成 |

### G01-治理与流程 要求
- 索引文件必须反映当前规范目录结构
- 索引更新必须原子性写入

### S04-质量保证 要求
- 索引生成必须可追溯
- 生成结果必须记录日志

## 实现映射

| 类/方法 | 规范要求 | 规范章节 |
|---------|----------|----------|
| `IndexGenerator` | 索引生成器 | G01-索引维护 |
| `running()` | 执行索引写入 | S04-索引生成 |

参见：
- specs/govs/G01-治理与流程.md
- specs/standards/S04-质量保证.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_info


class IndexGenerator:
    """
    负责写入索引文件。

    规范引用：
    - G01 治理与流程：索引维护
    - S04 质量保证：索引生成

    功能：
    1. 接收索引内容行列表
    2. 原子性写入索引文件
    3. 记录生成日志
    """

    def __init__(self, index_path: Path, lines: list[str]) -> None:
        """初始化索引写入器。"""
        self.index_path = index_path
        self.lines = lines

    def running(self) -> int:
        """执行索引写入。"""
        self.index_path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        log_info(f"已生成：{self.index_path}")
        return 0


def write_index(index_path: Path, lines: list[str]) -> int:
    """兼容函数入口：写入索引文件。"""
    return IndexGenerator(index_path, lines).running()
