"""
Markdown 章节结构校验公共逻辑。

## 规范引用

本校验器提供通用的章节校验功能，支持以下规范：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档规范 | S03 | 文档结构 |
| 质量保证 | S04 | 文档验证 |

### S03-文档规范 要求
- 文档必须使用 Markdown 格式
- 章节标题使用 `##` 二级标题
- 字段列表使用 `- 字段名: 值` 格式

### S04-质量保证 要求
- 关键字段必须存在且非空
- 文档验证必须可自动化执行

## 实现映射

| 函数 | 规范要求 | 规范章节 |
|------|----------|----------|
| `check_markdown_sections()` | 必需章节校验 | S03-文档结构 |
| `collecting_bullet_fields()` | 字段列表解析 | S03-字段格式 |
| `check_required_nonempty_bullets()` | 必需字段非空 | S04-文档验证 |

参见：
- specs/standards/S03-文档规范.md
- specs/standards/S04-质量保证.md
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from sdd.io import check_file_integrity, read_text_safe
from sdd.log import log_error, log_info
from sdd.utils import (
    extract_md_section, 
    normalize_md_token, 
    parse_bullet_list
)


def check_markdown_sections(
    path: Path,
    subject: str,
    required_sections: Sequence[str],
    missing_sections_message: str,
    passed_message: str,
    alternative_section_groups: Sequence[Sequence[str]] = (),
) -> int:
    """校验 Markdown 文档必需章节与可选分组章节。"""
    ok, error_message = check_file_integrity(path, subject)
    if not ok:
        log_error(error_message)
        return 1

    text = read_text_safe(path)
    missing = [section for section in required_sections if section not in text]
    for group in alternative_section_groups:
        if not any(section in text for section in group):
            missing.append(f"（{' 或 '.join(group)}）")

    if missing:
        log_error(missing_sections_message)
        for section in missing:
            log_error(f"- {section}")
        return 1

    log_info(passed_message)
    return 0




def check_required_nonempty_bullets(path: Path, section: str, required_labels: Sequence[str]) -> list[str]:
    """检查章节中给定字段是否存在且值非空。"""
    issues: list[str] = []
    lines = extract_md_section(read_text_safe(path), section)
    if not lines:
        issues.append(f"缺少章节：{section}")
        return issues

    fields = parse_bullet_list(lines)
    field_map: dict[str, list[str]] = {}
    for label, value in fields:
        field_map.setdefault(label, []).append(value)

    for required in required_labels:
        key = normalize_md_token(required)
        values = field_map.get(key)
        if not values:
            issues.append(f"{section} 缺少字段：{required}")
            continue
        if not any(value for value in values):
            issues.append(f"{section} 字段为空：{required}")
    return issues


def check_any_nonempty_prefixed_bullet(path: Path, section: str, prefix: str, display_name: str) -> list[str]:
    """检查章节中是否至少存在一个给定前缀的非空字段。"""
    lines = extract_md_section(read_text_safe(path), section)
    if not lines:
        return [f"缺少章节：{section}"]

    normalized_prefix = normalize_md_token(prefix)
    for label, value in parse_bullet_list(lines):
        if label.startswith(normalized_prefix) and value:
            return []
    return [f"{section} 缺少非空字段：{display_name}"]
