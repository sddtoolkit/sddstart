"""
SDD 命名规范校验引擎。

[SDD Traceability]
- Standard: S01 (文档编码规范)
- Standard: S02 (编码规范)
"""

from __future__ import annotations

import re
from pathlib import Path

# 特殊配置文件豁免名单
# Spec Ref: S01-7.1 (工具规范)
SPECIAL_CONFIG_FILES = {
    "govs/knowledge-sources.yaml",
    "meta/index/traceability.json",
    "meta/index/agent-dispatch.json",
    "meta/index/tool-adapters.json",
    "meta/index/reference-index.json",
}

# CCC 编码前缀
CCC_PREFIXES = ('RQ-', 'DS-', 'TK-', 'ADR-', 'G', 'S')


class NamingChecker:
    """
    负责校验项目文件命名是否符合 SDD 治理标准。
    
    Spec Ref: S01-6.1 (格式校验)
    """

    def __init__(self, banned_names: set[str], special_markdown_names: set[str]) -> None:
        self.banned_names = banned_names
        self.special_markdown_names = special_markdown_names

    def validate_path(self, path: Path, rel_path: str) -> list[str]:
        """
        全量校验给定路径的合规性。
        """
        if rel_path in SPECIAL_CONFIG_FILES:
            return []

        if path.name.lower() in self.banned_names:
            return [f"Banned filename: {rel_path}"]

        # 豁免 Python 内部文件
        if path.name in ("__init__.py", "requirements.txt"):
            return []

        if path.is_dir():
            return self._validate_base_name(path.name, f"Directory name invalid: {rel_path}")

        # 目录特定校验
        parts = Path(rel_path).parts
        if parts and parts[0] == "meta":
            return self._validate_meta_file(path, rel_path)
        elif parts and parts[0] == "tools":
            return self._validate_tool_file(path, rel_path)

        return self._validate_base_name(path.name, f"Naming style invalid: {rel_path}")

    def _validate_base_name(self, name: str, message: str) -> list[str]:
        """校验基础命名规则（小写、无空格、无下划线）。"""
        if any(ch.isupper() for ch in name) or "_" in name or " " in name:
            return [message]
        if not re.fullmatch(r"^[a-z0-9\-.]+$", name):
            return [f"Illegal characters in name: {name}"]
        return []

    def _validate_meta_file(self, path: Path, rel: str) -> list[str]:
        """校验元数据目录。 Spec Ref: S01-7.1"""
        allowed_sub = ("agents", "skills", "index", "tools")
        parts = Path(rel).parts
        if len(parts) < 2 or parts[1] not in allowed_sub:
            return [f"Unauthorized meta subdirectory: {rel}"]
        
        if parts[1] == "tools":
            if path.suffix not in (".py", ".md", ".txt", ".json"):
                return [f"Unsupported tool file type: {rel}"]
        elif path.suffix != ".md":
            return [f"Meta content must be Markdown: {rel}"]
            
        return self._validate_base_name(path.name, f"Meta naming invalid: {rel}")

    def _validate_tool_file(self, path: Path, rel: str) -> list[str]:
        """校验工具目录。"""
        if path.suffix not in (".py", ".md", ".txt"):
            return [f"Invalid tool extension: {rel}"]
        return self._validate_base_name(path.name, f"Tool naming invalid: {rel}")


def is_ccc_coded(filename: str) -> bool:
    """检查是否为受控的 CCC 编码文件。"""
    return any(filename.startswith(p) for p in CCC_PREFIXES)
