"""
代码质量检查器，提供轻量静态质量信号。

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 编码规范 | S02 | 代码组织、日志与可观测性 |
| 质量保证 | S04 | 代码评审 |
| 运营韧性 | S09 | 可观测性基线 |

### S02-编码规范 要求
- 模块边界必须清晰，职责单一
- 公共接口必须有文档或注释说明

### S04-质量保证 要求
- 关键模块必须评审通过方可合并
- 评审必须记录结论与问题清单

### S09-运营韧性 要求
- 代码实现必须提供关键路径埋点
- 保持可关联请求标识

## 实现映射

| 常量/方法 | 规范要求 | 规范章节 |
|-----------|----------|----------|
| `MAX_WARN_LINE` | 行长告警阈值 | S02-代码风格 |
| `MAX_ERROR_LINE` | 行长错误阈值 | S02-代码风格 |
| `MAX_ERROR_FILE_LINES` | 文件长度阈值 | S02-代码组织 |
| `TODO_MARK_PATTERN` | TODO/FIXME 检测 | S04-评审检查 |

参见：
- specs/standards/S02-编码规范.md
- specs/standards/S04-质量保证.md
- specs/standards/S09-运营韧性.md
"""

from __future__ import annotations

import re
from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error, log_info, log_warning

# ============================================================================
# 代码质量阈值
# ============================================================================
# 规范引用：S02-编码规范

# 支持的代码文件后缀
CODE_SUFFIXES = {".py", ".js", ".ts", ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp"}

# 行长阈值（字符数）
MAX_WARN_LINE = 120   # 超过此值告警
MAX_ERROR_LINE = 200  # 超过此值错误

# 文件行数阈值
MAX_ERROR_FILE_LINES = 2000  # 超过此值错误

# TODO/FIXME 标记模式
TODO_MARK_PATTERN = re.compile(r"\b(?:TODO|FIXME)\b")

# C 风格注释语言后缀
C_STYLE_SUFFIXES = {".js", ".ts", ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp"}


class QualityChecker:
    """执行代码长度、行长与 TODO/FIXME 质量检查。"""

    def __init__(self, repo_root: Path) -> None:
        """初始化质量检查器。"""
        self.repo_root = repo_root

    @staticmethod
    def extract_c_style_comment_fragment(line: str, in_block: bool) -> tuple[str, bool]:
        """提取 C 风格注释文本片段，并返回是否仍处于块注释中。"""
        comment_parts: list[str] = []
        cursor = 0

        while cursor < len(line):
            if in_block:
                end = line.find("*/", cursor)
                if end == -1:
                    comment_parts.append(line[cursor:])
                    return "".join(comment_parts), True
                comment_parts.append(line[cursor:end])
                cursor = end + 2
                in_block = False
                continue

            line_start = line.find("//", cursor)
            block_start = line.find("/*", cursor)
            candidates = [pos for pos in (line_start, block_start) if pos != -1]
            if not candidates:
                break
            start = min(candidates)
            if start == line_start:
                comment_parts.append(line[start + 2 :])
                break
            end = line.find("*/", start + 2)
            if end == -1:
                comment_parts.append(line[start + 2 :])
                in_block = True
                break
            comment_parts.append(line[start + 2 : end])
            cursor = end + 2

        return "".join(comment_parts), in_block

    @staticmethod
    def check_todo_marker_in_comment(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
        """判断当前行注释中是否包含 TODO/FIXME 标记。"""
        if suffix == ".py":
            hash_idx = line.find("#")
            comment_fragment = line[hash_idx + 1 :] if hash_idx != -1 else ""
            return bool(TODO_MARK_PATTERN.search(comment_fragment)), in_block

        if suffix in C_STYLE_SUFFIXES:
            comment_fragment, updated_in_block = QualityChecker.extract_c_style_comment_fragment(line, in_block)
            return bool(TODO_MARK_PATTERN.search(comment_fragment)), updated_in_block

        return False, in_block

    def collect_code_roots(self) -> list[Path]:
        """收集需要执行质量检查的常见代码目录。"""
        roots = [self.repo_root / name for name in ("src", "app", "lib", "services")]
        return [p for p in roots if p.is_dir()]

    def running(self) -> int:
        """执行代码质量检查。"""
        roots = self.collect_code_roots()
        if not roots:
            log_info("未发现代码目录（src/app/lib/services），跳过质量检查")
            return 0

        warnings: list[str] = []
        errors: list[str] = []

        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in CODE_SUFFIXES:
                    continue

                text = read_text_safe(path)
                lines = text.splitlines()

                if len(lines) > MAX_ERROR_FILE_LINES:
                    errors.append(f"{path}: 文件过长（{len(lines)} 行）")

                todo_count = 0
                in_block_comment = False
                for idx, line in enumerate(lines, start=1):
                    has_todo, in_block_comment = self.check_todo_marker_in_comment(
                        line,
                        path.suffix,
                        in_block_comment,
                    )
                    if has_todo:
                        todo_count += 1
                    length = len(line)
                    if length > MAX_ERROR_LINE:
                        errors.append(f"{path}:{idx} 行过长（{length}）")
                    elif length > MAX_WARN_LINE:
                        warnings.append(f"{path}:{idx} 行较长（{length}）")

                if todo_count > 0:
                    warnings.append(f"{path}: 存在 TODO/FIXME {todo_count} 处")

        if warnings:
            log_warning("代码质量告警：")
            for item in warnings:
                log_warning(f"- {item}")

        if errors:
            log_error("代码质量检查失败：")
            for item in errors:
                log_error(f"- {item}")
            return 1

        log_info("代码质量检查通过")
        return 0


def _extract_c_style_comment_fragment(line: str, in_block: bool) -> tuple[str, bool]:
    """兼容函数入口：提取 C 风格注释文本片段。"""
    return QualityChecker.extract_c_style_comment_fragment(line, in_block)


def _check_todo_marker_in_comment(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
    """兼容函数入口：判断注释 TODO/FIXME。"""
    return QualityChecker.check_todo_marker_in_comment(line, suffix, in_block)


def _collecting_code_roots(repo_root: Path) -> list[Path]:
    """兼容函数入口：收集代码目录。"""
    return QualityChecker(repo_root).collect_code_roots()


def check_code_quality(repo_root: Path) -> int:
    """兼容函数入口：执行代码质量检查。"""
    return QualityChecker(repo_root).running()
