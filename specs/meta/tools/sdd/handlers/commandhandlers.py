"""
命令处理函数映射校验与构建。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 工具清单与格式 | tool-adapters.json | 命令定义 |
| Agent协作宪章 | G05 | 工具适配 |

### tool-adapters.json 定义
- 命令处理函数必须与 CLI 子命令一一对应
- 缺失的处理函数必须报错

### G05-Agent协作宪章 要求
- 工具命令必须通过统一入口调用
- 命令处理必须返回标准退出码

## 命令清单

| 命令 | 功能 | 规范来源 |
|------|------|----------|
| initialize | 初始化 specs 目录 | G01-治理与流程 |
| generate-index | 生成索引文件 | S04-质量保证 |
| generate-traceability-matrix | 生成追溯矩阵 | S04-追溯完整性 |
| generate-agent-dispatch | 生成调度规则 | G05-Agent协作 |
| generate-tool-adapters | 生成工具适配 | tool-adapters.json |
| create-* | 创建各类文档 | S01-文档编码 |
| check-* | 执行各类检查 | S04-质量保证 |
| locate-document | 定位文档 | S01-引用编号 |
| trace-dependencies | 追踪依赖 | S06-证据关联 |

参见：
- specs/meta/index/tool-adapters.json
- specs/govs/G05-Agent协作宪章.md
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping

# 命令处理函数类型别名
CommandHandler = Callable[[argparse.Namespace], int]

# 规范引用：tool-adapters.json - 必需的命令处理函数
REQUIRED_HANDLER_KEYS: tuple[str, ...] = (
    "initialize",
    "version",
    "generate-index",
    "generate-traceability-matrix",
    "generate-agent-dispatch",
    "generate-tool-adapters",
    "create-requirement",
    "create-design",
    "create-adr",
    "create-task",
    "create-test",
    "create-release",
    "check-status",
    "check-quality-gates",
    "validate-requirement",
    "validate-design",
    "check-changelog",
    "check-governance",
    "check-dependencies",
    "check-code-quality",
    "check-completeness",
    "check-naming",
    "check-document-coding",
    "bundle-task-context",
    "trace-code",
    "locate-document",
    "read-document",
    "trace-dependencies",
    "rename-document",
    "build-reference-index",
    "find-references-to",
    "find-references-from",
    "update-references",
    "delete-references",
    "check-orphaned-references",
    "reference-report",
    "check-drift",
    "resolve-agent-dispatch",
    "list-tool-adapters",
    "add-tool-adapter",
    "remove-tool-adapter",
)


def build_handler_map(handlers: Mapping[str, CommandHandler]) -> dict[str, CommandHandler]:
    """
    校验并返回命令处理函数映射。

    规范引用：tool-adapters.json - 命令完整性检查

    Args:
        handlers: 命令名到处理函数的映射

    Returns:
        dict[str, CommandHandler]: 校验后的处理函数映射

    Raises:
        KeyError: 缺失必需的命令处理函数
    """
    missing = [key for key in REQUIRED_HANDLER_KEYS if key not in handlers]
    if missing:
        missing_text = ", ".join(missing)
        raise KeyError(f"缺少命令处理函数映射：{missing_text}")
    return dict(handlers)
