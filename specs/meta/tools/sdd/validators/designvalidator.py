"""
设计文档校验器，检查关键章节是否齐全。

## 规范引用

本校验器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档规范 | S03 | 设计文档结构 |
| 质量保证 | S04 | 设计验证 |
| 安全规范 | S02-安全 | 安全与隐私 |

### S03-文档规范 要求
- 设计文档必须包含：元信息、系统边界/架构概览、安全与隐私、可靠性与性能、追踪
- 元信息必须包含：文档编号、版本、负责人、日期

### S04-质量保证 要求
- 设计必须关联需求（关联需求）
- 设计必须关联任务（关联任务）

## 实现映射

| 常量/方法 | 规范要求 | 规范章节 |
|-----------|----------|----------|
| `REQUIRED_SECTIONS` | 设计文档必需章节 | S03-设计结构 |
| `ALTERNATIVE_SECTION_GROUPS` | 可选章节组 | S03-设计结构 |
| `check_design_file()` | 设计文档校验入口 | S04-设计验证 |

参见：
- specs/standards/S03-文档规范.md
- specs/standards/S04-质量保证.md
"""

from __future__ import annotations

from pathlib import Path

from sdd.io import read_text_safe
from sdd.log import log_error
from sdd.validators.sectionvalidator import (
    check_markdown_sections,
    check_required_nonempty_bullets,
)

# 规范引用：S03-文档规范 - 设计文档必需章节
REQUIRED_SECTIONS = (
    "## 元信息",
    "## 安全与隐私",
    "## 可靠性与性能",
    "## 追踪",
)

# 规范引用：S03-文档规范 - 可选章节组（至少包含其一）
ALTERNATIVE_SECTION_GROUPS = (
    ("## 系统边界", "## 架构概览"),
    ("## 接口列表", "## 接口与契约"),
)


class DesignValidator:
    """
    校验单个设计文档结构完整性。

    规范引用：
    - S03 文档规范：设计文档结构
    - S04 质量保证：设计验证

    检查规则：
    1. 必需章节：元信息、安全与隐私、可靠性与性能、追踪
    2. 可选章节组（至少其一）：系统边界/架构概览、接口列表/接口与契约
    3. 元信息字段：文档编号、版本、负责人、日期
    4. 系统边界字段：边界定义、外部依赖
    5. 架构概览字段：系统边界、关键组件
    6. 接口字段：对外接口
    7. 安全与隐私字段：认证与授权、数据保护
    8. 可靠性与性能字段：容量与性能目标
    9. 追踪字段：关联需求、关联任务
    """

    def __init__(self, path: Path) -> None:
        """初始化设计文档校验器。"""
        self.path = path

    def running(self) -> int:
        """执行设计文档校验。"""
        section_code = check_markdown_sections(
            path=self.path,
            subject="架构设计",
            required_sections=REQUIRED_SECTIONS,
            missing_sections_message="设计文档缺少关键章节：",
            passed_message="设计文档检查通过",
            alternative_section_groups=ALTERNATIVE_SECTION_GROUPS,
        )
        if section_code != 0:
            return section_code

        text = read_text_safe(self.path)
        issues: list[str] = []
        issues.extend(check_required_nonempty_bullets(self.path, "元信息", ("文档编号", "版本", "负责人", "日期")))
        if "## 系统边界" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "系统边界", ("边界定义", "外部依赖")))
        if "## 架构概览" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "架构概览", ("系统边界", "关键组件")))
        if "## 接口列表" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "接口列表", ("对外接口",)))
        if "## 接口与契约" in text:
            issues.extend(check_required_nonempty_bullets(self.path, "接口与契约", ("对外接口",)))
        issues.extend(check_required_nonempty_bullets(self.path, "安全与隐私", ("认证与授权", "数据保护")))
        issues.extend(check_required_nonempty_bullets(self.path, "可靠性与性能", ("容量与性能目标",)))
        issues.extend(check_required_nonempty_bullets(self.path, "追踪", ("关联需求", "关联任务")))

        if issues:
            log_error("设计文档存在占位或缺失内容：")
            for issue in issues:
                log_error(f"- {issue}")
            return 1
        return 0


def check_design_file(path: Path) -> int:
    """兼容函数入口：校验设计文档。"""
    return DesignValidator(path).running()
