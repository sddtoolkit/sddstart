"""
SDD CLI 通用辅助函数。

[SDD Traceability]
- Policy: G01 (治理与流程)
- Standard: S01 (文档编码规范)
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Sequence

from sdd.config import (
    DATE_COMPACT_FORMAT,
    DATE_ISO_FORMAT,
    MARKDOWN_HEADING_PATTERN,
    SEMVER_PATTERN,
    SPECS_DIR,
)
from sdd.io import read_text_safe, check_file_integrity
from sdd.log import log_error, log_info

# 有效的文档编号前缀
VALID_DOC_PREFIXES = ['RQ', 'DS', 'TK', 'ADR', 'G', 'S']

# 规范引用：S03-文档规范 - 字段列表格式 `- 字段名: 值`
BULLET_FIELD_PATTERN = re.compile(r"^\s*-\s+([^:：]+?)\s*[:：]\s*(.*?)\s*$")


def parse_bullet_list(lines: Sequence[str]) -> list[tuple[str, str]]:
    """解析 Markdown 章节中的列表字段。 Spec Ref: S03-3.1"""
    fields: list[tuple[str, str]] = []
    for raw in lines:
        match = BULLET_FIELD_PATTERN.match(raw)
        if not match:
            continue
        label = normalize_md_token(match.group(1))
        value = match.group(2).strip()
        fields.append((label, value))
    return fields


def extract_md_section(content: str, heading: str) -> List[str]:
    """提取指定二级标题 (##) 下的所有行。"""
    lines = content.splitlines()
    section_lines = []
    in_section = False
    target = normalize_md_token(heading)
    for line in lines:
        if line.startswith("## "):
            current_heading = normalize_md_token(line[3:])
            if current_heading == target:
                in_section = True
                continue
            elif in_section:
                break
        if in_section:
            section_lines.append(line)
    return section_lines


def copy_template(template_rel: str, target_rel: str) -> bool:
    """从 templates/ 拷贝模板到目标位置。"""
    template_path = SPECS_DIR / template_rel
    target_path = SPECS_DIR / target_rel
    if not template_path.exists():
        log_error(f"Template not found: {template_rel}")
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_path, target_path)
    return True


def write_file_safe(path: Path, content: str) -> bool:
    """仅当文件不存在时写入内容。"""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_gov_metadata(path: Path) -> None:
    """确保治理文档包含必需的元信息头。"""
    if not path.exists():
        return
    content = read_text_safe(path)
    if "## 元信息" not in content:
        header = f"# {path.stem}\n\n## 元信息\n- 版本：v1.0\n- 最后更新：{get_current_date_slug()}\n\n"
        path.write_text(header + content, encoding="utf-8")


def get_current_date_slug() -> str:
    """获取 YYYYMMDD 格式的日期。"""
    return datetime.now().strftime(DATE_COMPACT_FORMAT)


def get_yyww() -> str:
    """获取当前年份后两位 + 周数 (e.g. 2610)。"""
    return datetime.now().strftime("%y%U")


def get_next_nn(ccc: str, existing_ids: set[str]) -> str:
    """计算下一个可用的 NN 码。"""
    for i in range(1, 100):
        nn = f"{i:02d}"
        if f"{ccc}{nn}" not in [id_str.replace("-", "")[-5:] for id_str in existing_ids]:
            return nn
    return "AA"


def normalize_id(raw: str, prefix: str) -> str:
    """归一化标识符为大写标准格式。 Spec Ref: S01-2.1"""
    prefix_upper = prefix.upper()
    prefix_lower = prefix.lower()
    if raw.lower().startswith(prefix_lower + "-"):
        suffix = raw[len(prefix) + 1:].upper()
        return f"{prefix_upper}-{suffix}"
    return raw.upper()


def resolve_spec_path(ref_id: str) -> Tuple[Optional[Path], Optional[str], List[Path]]:
    """通过引用编号定位物理文件路径。 Spec Ref: S01-7.2"""
    prefix = ref_id.split('-')[0] if '-' in ref_id else ref_id
    if prefix not in VALID_DOC_PREFIXES:
        return None, f"Invalid prefix: {prefix}", []
    pattern = f"{ref_id}-*.md"
    matches = []
    for path in SPECS_DIR.rglob("*.md"):
        if "tools" in str(path) or "templates" in str(path):
            continue
        if re.match(pattern.replace("*", ".*"), path.name):
            matches.append(path)
    if len(matches) == 1:
        return matches[0], None, matches
    elif len(matches) > 1:
        return None, f"Ambiguous ID '{ref_id}'", matches
    return None, None, []


def normalize_md_token(text: str) -> str:
    """归一化 Markdown 标签文本。"""
    return text.strip().lower().replace("：", "").replace(":", "").replace("*", "").replace("`", "")


def read_first_heading(path: Path) -> str:
    """获取 Markdown 文档的第一个一级标题。"""
    if not path.exists(): return ""
    for line in read_text_safe(path).splitlines():
        if line.startswith("# "): return line[2:].strip()
    return ""


def list_top_directories() -> List[str]:
    """列出 specs/ 下的所有顶层受控目录。"""
    return [d.name for d in SPECS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]


def list_files_depth_two(base_dir: Path) -> List[Path]:
    """在指定目录下递归搜索深度为 2 的所有文件。"""
    files = []
    for p in base_dir.rglob("*"):
        if p.is_file() and len(p.relative_to(base_dir).parts) <= 2:
            files.append(p)
    return files


def resolve_safe_path(rel_path: str | None) -> Optional[Path]:
    """
    将相对路径解析为绝对路径，并确保其位于 specs/ 目录内。
    
    Returns:
        Path 对象或 None（若路径非法或越界）
    """
    if not rel_path: return None
    try:
        abs_path = (SPECS_DIR / rel_path).resolve()
        if SPECS_DIR in abs_path.parents or abs_path == SPECS_DIR:
            return abs_path
    except Exception:
        pass
    return None


def check_path_exists(path: Path, subject: str) -> int:
    """检查路径是否存在并报错。"""
    passed, error = check_file_integrity(path, subject)
    if not passed:
        log_error(error)
        return 1
    return 0


def validate_slug(raw: str) -> Optional[str]:
    """校验并清洗 Slug 字符串。"""
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]+", "-", raw).strip("-").lower()
    return cleaned if cleaned else None


def validate_semver(version: str) -> bool:
    """验证语义化版本格式。"""
    return bool(SEMVER_PATTERN.match(version))


def count_specs_by_dir(specs_dir: Path) -> dict[str, int]:
    """按顶层目录统计 Markdown 文件数量。"""
    stats = {}
    for d in specs_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            stats[d.name] = len(list(d.rglob("*.md")))
    return stats


def extract_registered_ids(index_text: str) -> set[str]:
    """从 index.md 提取已登记的文件路径。"""
    return set(re.findall(r"`([^`]+\.md)`", index_text))


def check_structured_bullets(path: Path, section: str, labels: Sequence[str]) -> list[str]:
    """校验指定章节的 Bullet 列表是否完备。"""
    from sdd.validators.sectionvalidator import check_required_nonempty_bullets
    return check_required_nonempty_bullets(path, section, labels)
