"""
文档依赖追踪器，根据文档编号检索关联的需求、设计、任务及代码实现。

## 规范引用

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档编码规范 | S01 | 引用编号规则 |
| 质量保证 | S04 | 追溯完整性 |
| 证据规范 | S06 | 证据关联 |
| 编码规范 | S02 | 规范来源标记 |

### S01-文档编码规范 要求
- 引用编号格式：RQ-XXXXX, DS-XXXXX, TK-XXXXXXXXX, ADR-XXXXX, GNN, SNN
- 引用编号用于文档间交叉引用

### S04-质量保证 要求
- 追溯链路必须完整
- 需求必须关联设计、任务、测试

### S06-证据规范 要求
- 代码实现必须可追溯到规范来源
- 代码文件应包含规范标记（SPEC_MARK）

### S02-编码规范 要求
- 代码必须包含规范来源标记
- 漂移（代码与规范不一致）必须可检测

## 追踪结果结构

```
DependencyTraceResult
├── ref_id: str              # 查询的文档编号
├── source_doc               # 源文档信息
├── related_reqs             # 关联需求列表
├── related_designs          # 关联设计列表
├── related_tasks            # 关联任务列表
├── related_tests            # 关联测试列表
├── related_adrs             # 关联决策列表
├── code_refs                # 代码引用列表
└── errors                   # 错误信息列表
```

## 实现映射

| 类/方法 | 规范要求 | 规范章节 |
|---------|----------|----------|
| `DependencyTracer` | 依赖追踪器 | S04-追溯管理 |
| `trace()` | 执行追踪查询 | S06-证据关联 |
| `_find_code_references()` | 查找代码引用 | S02-规范标记 |

参见：
- specs/standards/S01-文档编码规范.md
- specs/standards/S02-编码规范.md
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from sdd.io import read_text_safe
from sdd.config import SPEC_MARK, SUPPORTED_CODE_SUFFIXES
from sdd.utils import resolve_spec_path


@dataclass
class CodeReference:
    """
    代码引用信息。

    规范引用：S02-编码规范、S06-证据规范

    Attributes:
        file_path: 代码文件路径
        line_number: 引用行号
        context: 引用上下文（代码片段）
        module_name: 模块名
        function_name: 函数/类名
    """
    file_path: str
    line_number: int
    context: str
    module_name: str = ""
    function_name: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "context": self.context,
            "module": self.module_name,
            "function": self.function_name,
        }


@dataclass
class DocumentReference:
    """
    文档引用信息。

    规范引用：S01-文档编码规范、S04-质量保证

    Attributes:
        doc_id: 文档编号（如 RQ-10102）
        doc_path: 文档相对路径
        doc_title: 文档标题
        doc_type: 文档类型（requirement/design/task/test/adr/governance/standard）
        context: 引用上下文
    """
    doc_id: str
    doc_path: str
    doc_title: str
    doc_type: str
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.doc_id,
            "path": self.doc_path,
            "title": self.doc_title,
            "type": self.doc_type,
            "context": self.context,
        }


@dataclass
class DependencyTraceResult:
    """
    依赖追踪结果。

    规范引用：S04-质量保证、S06-证据规范

    Attributes:
        ref_id: 查询的文档编号
        source_doc: 源文档信息
        related_reqs: 关联需求列表
        related_designs: 关联设计列表
        related_tasks: 关联任务列表
        related_tests: 关联测试列表
        related_adrs: 关联决策列表
        code_refs: 代码引用列表
        errors: 错误信息列表
    """
    ref_id: str
    source_doc: Optional[DocumentReference] = None
    related_reqs: list[DocumentReference] = field(default_factory=list)
    related_designs: list[DocumentReference] = field(default_factory=list)
    related_tasks: list[DocumentReference] = field(default_factory=list)
    related_tests: list[DocumentReference] = field(default_factory=list)
    related_adrs: list[DocumentReference] = field(default_factory=list)
    code_refs: list[CodeReference] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "ref_id": self.ref_id,
            "source_doc": self.source_doc.to_dict() if self.source_doc else None,
            "related": {
                "requirements": [r.to_dict() for r in self.related_reqs],
                "designs": [r.to_dict() for r in self.related_designs],
                "tasks": [r.to_dict() for r in self.related_tasks],
                "tests": [r.to_dict() for r in self.related_tests],
                "adrs": [r.to_dict() for r in self.related_adrs],
            },
            "code_refs": [c.to_dict() for c in self.code_refs],
            "errors": self.errors,
        }


class DependencyTracer:
    """
    文档依赖追踪器。

    规范引用：
    - S01 文档编码规范：文档编号格式
    - S04 质量保证：追溯完整性
    - S06 证据规范：证据关联

    功能：
    1. 根据文档编号定位源文档
    2. 查找所有引用该编号的文档
    3. 查找代码中的规范来源标记
    4. 生成完整的依赖追踪结果

    支持的文档类型：
    - RQ: 需求文档
    - DS: 设计文档
    - TK: 任务文档
    - ADR: 决策文档
    - G: 治理文档
    - S: 标准文档
    - TEST: 测试文档
    """

    # 规范引用：S01-文档编码规范 - 文档类型映射
    DOC_TYPE_MAP = {
        "RQ": "requirement",
        "DS": "design",
        "TK": "task",
        "ADR": "adr",
        "G": "governance",
        "S": "standard",
        "TEST": "test",
    }

    # 规范引用：S01-文档编码规范 - 引用标识模式
    REF_PATTERNS = {
        "RQ": re.compile(r"\bRQ-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "DS": re.compile(r"\bDS-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "TK": re.compile(r"\bTK-[0-9]{3,}[0-9]{4,}[0-9A-Z]{2,}\b"),
        "ADR": re.compile(r"\bADR-[0-9]{3,}[0-9A-Z]{2,}\b"),
        "G": re.compile(r"\bG[0-9]{2,}\b"),
        "S": re.compile(r"\bS[0-9]{2,}\b"),
    }
    
    def __init__(self, specs_dir: Path, repo_root: Path | None = None):
        self.specs_dir = specs_dir
        self.repo_root = repo_root or specs_dir.parent
        
    def trace(self, ref_id: str) -> DependencyTraceResult:
        """
        追踪文档依赖关系
        
        Args:
            ref_id: 文档编号，如 "RQ-10102"
            
        Returns:
            DependencyTraceResult: 追踪结果
        """
        result = DependencyTraceResult(ref_id=ref_id)
        
        # 1. 定位源文档
        source_path = self._locate_source_document(ref_id)
        if not source_path:
            result.errors.append(f"未找到文档: {ref_id}")
            return result
            
        result.source_doc = self._parse_document_info(source_path, ref_id)
        
        # 2. 在specs目录中搜索所有引用该编号的文档
        self._find_related_documents(ref_id, result)
        
        # 3. 在代码中搜索引用该编号的位置
        self._find_code_references(ref_id, result)
        
        return result
    
    def _locate_source_document(self, ref_id: str) -> Path | None:
        """定位源文档"""
        path, _, _ = resolve_spec_path(ref_id)
        return path
    def _parse_document_info(self, path: Path, doc_id: str) -> DocumentReference:
        """解析文档信息"""
        prefix = doc_id.split("-")[0] if "-" in doc_id else doc_id
        doc_type = self.DOC_TYPE_MAP.get(prefix, "unknown")
        
        # 读取标题
        title = self._extract_title(path)
        rel_path = path.relative_to(self.specs_dir)
        
        return DocumentReference(
            doc_id=doc_id,
            doc_path=str(rel_path),
            doc_title=title,
            doc_type=doc_type,
        )
    
    def _extract_title(self, path: Path) -> str:
        """提取文档标题"""
        try:
            text = read_text_safe(path)
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
        except Exception:
            pass
        return path.stem
    
    def _find_related_documents(self, ref_id: str, result: DependencyTraceResult) -> None:
        """查找关联文档"""
        # 扫描所有可追溯目录
        traceable_dirs = ["1-reqs", "adrs", "2-designs", "3-tasks", "tests", "releases", "govs", "standards"]
        
        for dir_name in traceable_dirs:
            base_dir = self.specs_dir / dir_name
            if not base_dir.exists():
                continue
                
            for doc_path in base_dir.rglob("*.md"):
                if "templates" in str(doc_path):
                    continue
                    
                try:
                    text = read_text_safe(doc_path)
                    if ref_id in text:
                        # 提取引用的上下文
                        context = self._extract_context(text, ref_id)
                        
                        # 确定文档类型和ID
                        doc_id = self._extract_doc_id_from_filename(doc_path.name)
                        prefix = doc_id.split("-")[0] if doc_id and "-" in doc_id else ""
                        doc_type = self.DOC_TYPE_MAP.get(prefix, "unknown")
                        
                        doc_ref = DocumentReference(
                            doc_id=doc_id or doc_path.stem,
                            doc_path=str(doc_path.relative_to(self.specs_dir)),
                            doc_title=self._extract_title(doc_path),
                            doc_type=doc_type,
                            context=context,
                        )
                        
                        # 分类存储
                        if prefix == "RQ":
                            result.related_reqs.append(doc_ref)
                        elif prefix == "DS":
                            result.related_designs.append(doc_ref)
                        elif prefix == "TK":
                            result.related_tasks.append(doc_ref)
                        elif prefix == "TEST" or "test" in str(doc_path).lower():
                            result.related_tests.append(doc_ref)
                        elif prefix == "ADR":
                            result.related_adrs.append(doc_ref)
                        elif prefix == "G":
                            # 治理文档归入 tests 类别显示（或可以新增 governance 类别）
                            result.related_tests.append(doc_ref)
                        elif prefix == "S":
                            # 标准文档根据内容判断
                            if "测试" in text[:500]:
                                result.related_tests.append(doc_ref)
                            else:
                                result.related_designs.append(doc_ref)
                except Exception:
                    continue
        
        # 去重并排序
        result.related_reqs = self._deduplicate_docs(result.related_reqs)
        result.related_designs = self._deduplicate_docs(result.related_designs)
        result.related_tasks = self._deduplicate_docs(result.related_tasks)
        result.related_tests = self._deduplicate_docs(result.related_tests)
        result.related_adrs = self._deduplicate_docs(result.related_adrs)
    
    def _extract_context(self, text: str, ref_id: str, context_lines: int = 2) -> str:
        """提取引用上下文"""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if ref_id in line:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = " | ".join(lines[start:end])
                # 截断过长内容
                if len(context) > 150:
                    context = context[:147] + "..."
                return context
        return ""
    
    def _extract_doc_id_from_filename(self, filename: str) -> str:
        """从文件名提取文档编号"""
        if not filename.endswith(".md"):
            return filename
        
        name = filename[:-3]
        parts = name.split("-")
        
        if len(parts) < 2:
            return filename
        
        prefix = parts[0]
        
        if prefix in ["RQ", "DS", "ADR"]:
            if len(parts) >= 3 and len(parts[1]) >= 5:
                return f"{parts[0]}-{parts[1][:5]}"
        elif prefix == "TK":
            if len(parts) >= 3 and len(parts[1]) >= 9:
                return f"{parts[0]}-{parts[1][:9]}"
        elif prefix in ["G", "S"]:
            if len(parts) >= 2:
                return f"{parts[0]}-{parts[1]}"
        
        return filename
    
    def _deduplicate_docs(self, docs: list[DocumentReference]) -> list[DocumentReference]:
        """去重文档列表"""
        seen = set()
        result = []
        for doc in docs:
            if doc.doc_id not in seen:
                seen.add(doc.doc_id)
                result.append(doc)
        return sorted(result, key=lambda x: x.doc_id)
    
    def _find_code_references(self, ref_id: str, result: DependencyTraceResult) -> None:
        """查找代码引用"""
        src_dir = self.repo_root / "src"
        if not src_dir.exists():
            # 尝试其他常见的源代码目录
            for alt_dir in [self.repo_root / "code", self.repo_root / "lib", self.repo_root]:
                if alt_dir.exists():
                    src_dir = alt_dir
                    break
            else:
                return
        
        for file_path in src_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in SUPPORTED_CODE_SUFFIXES:
                continue
            if "__pycache__" in str(file_path):
                continue
                
            try:
                content = read_text_safe(file_path)
                if ref_id not in content and SPEC_MARK not in content:
                    continue
                    
                # 查找引用位置
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    if ref_id in line or (SPEC_MARK in line and self._is_related_to_ref(line, ref_id)):
                        code_ref = CodeReference(
                            file_path=str(file_path.relative_to(self.repo_root)),
                            line_number=line_num,
                            context=line.strip()[:100],
                            module_name=self._extract_module_name(file_path),
                            function_name=self._extract_function_name(lines, line_num),
                        )
                        result.code_refs.append(code_ref)
            except Exception:
                continue
    
    def _is_related_to_ref(self, line: str, ref_id: str) -> bool:
        """检查行是否与引用编号相关"""
        # 简单的启发式检查：行附近是否包含引用编号
        return ref_id in line or True  # 如果包含SPEC_MARK则认为相关
    
    def _extract_module_name(self, path: Path) -> str:
        """提取模块名"""
        # 根据文件路径和扩展名推断模块名
        if path.suffix == ".py":
            return path.stem
        elif path.suffix in [".js", ".ts"]:
            return path.stem
        elif path.suffix == ".go":
            return path.stem
        elif path.suffix == ".rs":
            return path.stem
        return ""
    
    def _extract_function_name(self, lines: list[str], line_num: int) -> str:
        """提取当前位置的函数/类名"""
        # 向上查找最近的函数或类定义
        func_patterns = [
            (r"^\s*def\s+(\w+)", "function"),
            (r"^\s*class\s+(\w+)", "class"),
            (r"^\s*(?:async\s+)?function\s+(\w+)", "function"),
            (r"^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:async)?\s*(?:\w+\s+)?(\w+)\s*\(", "function"),
            (r"^\s*fn\s+(\w+)", "function"),
        ]
        
        for i in range(line_num - 1, -1, -1):
            line = lines[i]
            for pattern, kind in func_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1)
        return ""


def trace_dependencies(specs_dir: Path, ref_id: str, repo_root: Path | None = None) -> DependencyTraceResult:
    """兼容函数入口：追踪文档依赖"""
    return DependencyTracer(specs_dir, repo_root).trace(ref_id)
