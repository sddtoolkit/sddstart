"""
需求文档校验器，检查关键章节是否完整。

## 规范引用

本校验器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档规范 | S03 | 需求文档结构 |
| 质量保证 | S04 | 需求验证 |

### S03-文档规范 要求
- 需求文档必须包含：元信息、目标与范围、功能需求、验收标准、追踪
- 元信息必须包含：文档编号、版本、负责人、日期

### S04-质量保证 要求
- 需求必须可追溯到设计、任务、测试
- 功能需求应使用 FR-* 标识
- 验收标准应使用 AC-* 标识

## 实现映射

| 常量/方法 | 规范要求 | 规范章节 |
|-----------|----------|----------|
| `REQUIRED_SECTIONS` | 需求文档必需章节 | S03-需求结构 |
| `check_requirement_file()` | 需求文档校验入口 | S04-需求验证 |

参见：
- specs/standards/S03-文档规范.md
- specs/standards/S04-质量保证.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.log import log_error
from sdd.validators.sectionvalidator import (
    check_any_nonempty_prefixed_bullet,
    check_markdown_sections,
    check_required_nonempty_bullets,
)

# 规范引用：S03-文档规范 - 需求文档必需章节
REQUIRED_SECTIONS = (
    "## 元信息",
    "## 目标与范围",
    "## 功能需求",
    "## 验收标准",
    "## 追踪",
)


class RequirementValidator:
    """
    校验单个需求文档结构完整性。

    规范引用：
    - S03 文档规范：需求文档结构
    - S04 质量保证：需求验证

    检查规则：
    1. 必需章节：元信息、目标与范围、功能需求、验收标准、追踪
    2. 元信息字段：文档编号、版本、负责人、日期
    3. 目标与范围字段：目标、范围
    4. 追踪字段：关联设计、关联任务、关联测试
    5. 功能需求：至少一个 FR-* 条目
    6. 验收标准：至少一个 AC-* 条目
    """

    def __init__(self, path: Path) -> None:
        """初始化需求文档校验器。"""
        self.path = path

    def running(self) -> int:
        """执行需求文档校验。"""
        section_code = check_markdown_sections(
            path=self.path,
            subject="需求文档",
            required_sections=REQUIRED_SECTIONS,
            missing_sections_message="需求文档缺少关键章节：",
            passed_message="需求文档检查通过",
        )
        if section_code != 0:
            return section_code

        issues: list[str] = []
        issues.extend(check_required_nonempty_bullets(self.path, "元信息", ("文档编号", "版本", "负责人", "日期")))
        issues.extend(check_required_nonempty_bullets(self.path, "目标与范围", ("目标", "范围")))
        issues.extend(check_required_nonempty_bullets(self.path, "追踪", ("关联设计", "关联任务", "关联测试")))
        issues.extend(check_any_nonempty_prefixed_bullet(self.path, "功能需求", "FR-", "FR-*"))
        issues.extend(check_any_nonempty_prefixed_bullet(self.path, "验收标准", "AC-", "AC-*"))

        if issues:
            log_error("需求文档存在占位或缺失内容：")
            for issue in issues:
                log_error(f"- {issue}")
            return 1
        return 0


def check_requirement_file(path: Path) -> int:
    """兼容函数入口：校验需求文档。"""
    return RequirementValidator(path).running()
