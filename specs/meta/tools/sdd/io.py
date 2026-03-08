"""
SDD 基础 IO 工具包。

[SDD Traceability]
- Policy: G01 (治理与流程)
- Standard: S03 (文档规范)
"""

from __future__ import annotations

from pathlib import Path
from sdd.log import log_warning


def read_text_safe(path: Path) -> str:
    """
    安全读取文本文件，自动处理编码异常并支持替换模式。
    
    Spec Ref: S03-1.1 (编码强制要求 UTF-8)
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        log_warning(f"Encoding Warning: {path} is not UTF-8 ({exc}). Using fallback.")
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError(f"Failed to read file: {path} ({exc})") from exc


def check_file_integrity(
    path: Path, 
    subject: str,
    missing_template: str = "Missing {subject}: {path}",
    empty_template: str = "{subject} is empty: {path}"
) -> tuple[bool, str]:
    """
    检查文件完整性（是否存在且非空）。
    
    Spec Ref: S04-3.2 (证据完整性校验)
    """
    if not path.exists():
        return False, missing_template.format(subject=subject, path=path)
    if path.stat().st_size == 0:
        return False, empty_template.format(subject=subject, path=path)
    return True, ""
