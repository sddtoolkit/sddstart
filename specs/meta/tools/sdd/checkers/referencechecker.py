"""
文档引用关系管理器，提供引用查询、更新、删除和索引维护功能。

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档编码规范 | S01 | 引用编号规则 |
| 质量保证 | S04 | 追溯完整性 |
| 证据规范 | S06 | 证据关联 |

### S01-文档编码规范 要求
- 引用编号用于文档间的交叉引用
- 引用编号在整个 specs/ 目录下必须唯一

### S04-质量保证 要求
- 追溯链路必须完整且可验证
- 缺失关联应作为错误报告

### S06-证据规范 要求
- 证据必须关联到对应任务、变更或发布记录
- 确保可追溯

## 实现映射

| 方法 | 规范要求 | 规范章节 |
|------|----------|----------|
| `CCC_DOC_PATTERN` | CCC 文档路径匹配 | S01-3.x |
| `REF_ID_PATTERNS` | 引用编号提取模式 | S01-2.1 |
| `extract_ref_id_from_filename()` | 引用编号提取 | S01-2.1 |
| `build_reference_index()` | 构建引用索引 | S04-追溯管理 |
| `check_orphaned_references()` | 孤立引用检查 | S06-证据关联 |

参见：
- specs/standards/S01-文档编码规范.md
- specs/standards/S04-质量保证.md
- specs/standards/S06-证据规范.md
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional


@dataclass
class Reference:
    """
    引用关系数据类。

    规范引用：S01-2.1 引用编号定义、S06-证据关联

    Attributes:
        source_file: 源文件路径（相对specs）
        source_ref_id: 源文件引用编号（如 G01, S01, RQ-10102）
        target_file: 目标文件路径（相对specs）
        target_ref_id: 目标文件引用编号
        line_number: 引用所在行号
        context: 引用上下文（整行内容）
        ref_type: 引用类型（doc/index/code）
    """
    source_file: str  # 源文件路径（相对specs）
    source_ref_id: str  # 源文件引用编号（如 G01, S01, RQ-10102）
    target_file: str  # 目标文件路径（相对specs）
    target_ref_id: str  # 目标文件引用编号
    line_number: int  # 引用所在行号
    context: str  # 引用上下文（整行内容）
    ref_type: str  # 引用类型：doc（文档引用）、index（索引引用）、code（代码引用）


class ReferenceManager:
    """
    文档引用关系管理器。

    规范引用：
    - S01 文档编码规范：引用编号规则
    - S04 质量保证：追溯完整性
    - S06 证据规范：证据关联

    功能：
    1. 扫描并建立文档间的引用关系
    2. 构建正向/反向引用索引
    3. 检查孤立引用（引用不存在的文档）
    4. 批量更新引用编号
    5. 生成引用关系报告
    """

    # 规范引用：S01-3.x - CCC编码文档路径匹配模式
    CCC_DOC_PATTERN = re.compile(
        r'specs/([a-zA-Z0-9_\-]+)/(RQ-\d{5}|DS-\d{5}|TK-\d{9}|ADR-\d{5}|G\d{2}|S\d{2}|[^\s\'"`)]+\.(?:md|yaml))'
    )

    # 规范引用：S01-2.1 - 引用编号提取模式
    REF_ID_PATTERNS = {
        'RQ': re.compile(r'RQ-(\d{3})(\d{2})'),
        'DS': re.compile(r'DS-(\d{3})(\d{2})'),
        'TK': re.compile(r'TK-(\d{3})(\d{4})(\d{2})'),
        'ADR': re.compile(r'ADR-(\d{3})(\d{2})'),
        'G': re.compile(r'G(\d{2})'),
        'S': re.compile(r'S(\d{2})'),
    }
    
    def __init__(self, specs_dir: str = "specs"):
        self.specs_dir = Path(specs_dir)
        self.index_path = self.specs_dir / "meta/index" / "reference-index.json"
        self.references: List[Reference] = []
        self._ref_id_cache: Dict[str, str] = {}  # 文件路径 -> 引用编号的缓存
    
    def extract_ref_id_from_filename(self, filename: str) -> Optional[str]:
        """从文件名提取引用编号"""
        if not filename.endswith('.md'):
            return None
        
        name = filename[:-3]  # 去掉.md
        parts = name.split('-')
        
        if len(parts) < 1:
            return None
        
        prefix = parts[0]
        
        # RQ-10102-xxx → RQ-10102
        if prefix in ['RQ', 'DS', 'ADR'] and len(parts) >= 2:
            return f"{prefix}-{parts[1]}"
        
        # TK-201260901-xxx → TK-201260901
        if prefix == 'TK' and len(parts) >= 2:
            return f"{prefix}-{parts[1]}"
        
        # G01-xxx → G01
        if prefix.startswith('G') and len(prefix) >= 3:
            return prefix
        
        # S01-xxx → S01
        if prefix.startswith('S') and len(prefix) >= 3:
            return prefix
        
        return None
    
    def scan_all_references(self) -> List[Reference]:
        """
        扫描所有文档中的引用关系
        
        Returns:
            引用关系列表
        """
        self.references = []
        
        for root, _, files in os.walk(self.specs_dir):
            # 跳过工具和缓存目录
            if 'tools' in root or '__pycache__' in root:
                continue
            
            for file in files:
                if not (file.endswith('.md') or file.endswith('.py')):
                    continue
                
                source_path = Path(root) / file
                source_rel = source_path.relative_to(self.specs_dir)
                source_ref_id = self.extract_ref_id_from_filename(file)
                
                # 读取文件内容
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except Exception:
                    continue
                
                # 扫描每一行的引用
                for line_num, line in enumerate(lines, 1):
                    matches = self.CCC_DOC_PATTERN.finditer(line)
                    for match in matches:
                        target_rel = match.group(0)
                        target_file = target_rel.replace('specs/', '')
                        target_ref_id = self.extract_ref_id_from_filename(Path(target_file).name)
                        
                        # 确定引用类型
                        if file.endswith('.py'):
                            ref_type = 'code'
                        elif 'meta/index' in str(source_rel):
                            ref_type = 'index'
                        else:
                            ref_type = 'doc'
                        
                        ref = Reference(
                            source_file=str(source_rel),
                            source_ref_id=source_ref_id or str(source_rel),
                            target_file=target_file,
                            target_ref_id=target_ref_id or target_file,
                            line_number=line_num,
                            context=line.strip(),
                            ref_type=ref_type
                        )
                        self.references.append(ref)
        
        return self.references
    
    def build_reference_index(self) -> Dict:
        """
        构建引用索引数据结构
        
        Returns:
            索引字典
        """
        if not self.references:
            self.scan_all_references()
        
        # 正向索引：文档 -> 引用的文档
        forward_index: Dict[str, List[Dict]] = {}
        # 反向索引：文档 -> 被哪些文档引用
        reverse_index: Dict[str, List[Dict]] = {}
        # 统计信息
        stats = {
            'total_references': len(self.references),
            'total_source_files': len(set(r.source_file for r in self.references)),
            'total_target_files': len(set(r.target_file for r in self.references)),
        }
        
        for ref in self.references:
            # 正向索引
            if ref.source_file not in forward_index:
                forward_index[ref.source_file] = []
            forward_index[ref.source_file].append({
                'target_ref_id': ref.target_ref_id,
                'target_file': ref.target_file,
                'line_number': ref.line_number,
                'context': ref.context,
                'ref_type': ref.ref_type
            })
            
            # 反向索引
            if ref.target_file not in reverse_index:
                reverse_index[ref.target_file] = []
            reverse_index[ref.target_file].append({
                'source_ref_id': ref.source_ref_id,
                'source_file': ref.source_file,
                'line_number': ref.line_number,
                'context': ref.context,
                'ref_type': ref.ref_type
            })
        
        return {
            'version': '1.0',
            'stats': stats,
            'forward_index': forward_index,  # 文档引用了谁
            'reverse_index': reverse_index,  # 文档被谁引用
        }
    
    def save_index(self) -> None:
        """保存引用索引到文件"""
        index = self.build_reference_index()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def load_index(self) -> Dict:
        """从文件加载引用索引"""
        if not self.index_path.exists():
            return {}
        with open(self.index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def find_references_to(self, ref_id: str) -> List[Dict]:
        """
        查询哪些文档引用了指定的文档编号
        
        Args:
            ref_id: 目标文档编号（如 G01, S01, RQ-10102）
        
        Returns:
            引用该文档的列表
        """
        index = self.load_index()
        reverse_index = index.get('reverse_index', {})
        
        results = []
        for target_file, refs in reverse_index.items():
            # target_file 可能是 "govs/G04" 或 "govs/G04-xxx.md" 格式
            # 从路径中提取最后一部分
            target_name = Path(target_file).name
            
            # 如果target_name不以.md结尾，说明是缩写格式（如G04）
            # 直接使用target_name作为target_ref_id
            if '.' not in target_name:
                target_ref_id = target_name
            else:
                # 完整文件名，提取引用编号
                extracted = self.extract_ref_id_from_filename(target_name)
                target_ref_id = extracted if extracted else target_name
            
            if target_ref_id == ref_id:
                results.extend(refs)
        
        return results
    
    def find_references_from(self, ref_id: str) -> List[Dict]:
        """
        查询指定文档引用了哪些文档
        
        Args:
            ref_id: 源文档编号
        
        Returns:
            该文档引用的列表
        """
        index = self.load_index()
        forward_index = index.get('forward_index', {})
        
        results = []
        for source_file, refs in forward_index.items():
            source_ref_id = self.extract_ref_id_from_filename(Path(source_file).name)
            if source_ref_id == ref_id:
                results.extend(refs)
        
        return results
    
    def update_references(self, old_ref_id: str, new_ref_id: str, 
                         dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        批量更新引用关系（将旧编号替换为新编号）
        
        Args:
            old_ref_id: 旧引用编号
            new_ref_id: 新引用编号
            dry_run: 是否仅预览，不实际修改
        
        Returns:
            (更新数量, 更新日志)
        """
        # 首先找到新编号对应的文件
        new_file_pattern = None
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                current_ref_id = self.extract_ref_id_from_filename(file)
                if current_ref_id == new_ref_id:
                    new_file_pattern = f"specs/{Path(root).relative_to(self.specs_dir)}/{file}"
                    new_file_pattern = new_file_pattern.replace(str(self.specs_dir) + '/', '')
                    break
            if new_file_pattern:
                break
        
        if not new_file_pattern:
            return 0, [f"错误：未找到引用编号 {new_ref_id} 对应的文件"]
        
        # 找到需要更新的引用
        references_to_update = self.find_references_to(old_ref_id)
        
        if dry_run:
            log = [f"[预览] 将更新 {len(references_to_update)} 处引用:"]
            for ref in references_to_update:
                log.append(f"  - {ref['source_file']}:{ref['line_number']}")
            return len(references_to_update), log
        
        # 实际更新
        updated_count = 0
        log = []
        
        # 按文件分组
        files_to_update: Dict[str, List[Tuple[int, str, str]]] = {}
        for ref in references_to_update:
            source_file = ref['source_file']
            if source_file not in files_to_update:
                files_to_update[source_file] = []
            files_to_update[source_file].append((
                ref['line_number'],
                ref['context'],
                ref['target_file']
            ))
        
        for source_file, refs in files_to_update.items():
            source_path = self.specs_dir / source_file
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, old_context, old_target in refs:
                    old_ref_pattern = f"specs/{old_target}"
                    new_ref_pattern = new_file_pattern
                    
                    if old_ref_pattern in lines[line_num - 1]:
                        lines[line_num - 1] = lines[line_num - 1].replace(
                            old_ref_pattern, new_ref_pattern
                        )
                        updated_count += 1
                        log.append(f"已更新: {source_file}:{line_num}")
                
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
            except Exception as e:
                log.append(f"错误: {source_file} - {e}")
        
        # 更新索引
        if updated_count > 0:
            self.scan_all_references()
            self.save_index()
        
        return updated_count, log
    
    def delete_references_to(self, ref_id: str, dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        删除所有对指定文档的引用（将引用标记为过时）
        
        Args:
            ref_id: 要删除引用的文档编号
            dry_run: 是否仅预览
        
        Returns:
            (删除数量, 日志)
        """
        references_to_delete = self.find_references_to(ref_id)
        
        if dry_run:
            log = [f"[预览] 将删除 {len(references_to_delete)} 处引用:"]
            for ref in references_to_delete:
                log.append(f"  - {ref['source_file']}:{ref['line_number']}")
            return len(references_to_delete), log
        
        # 实际删除（标记为过时）
        deleted_count = 0
        log = []
        
        files_to_update: Dict[str, List[Tuple[int, str]]] = {}
        for ref in references_to_delete:
            source_file = ref['source_file']
            if source_file not in files_to_update:
                files_to_update[source_file] = []
            files_to_update[source_file].append((ref['line_number'], ref['context']))
        
        for source_file, refs in files_to_update.items():
            source_path = self.specs_dir / source_file
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, context in refs:
                    # 在行尾添加 [引用已过时] 标记
                    if '[引用已过时]' not in lines[line_num - 1]:
                        lines[line_num - 1] = lines[line_num - 1].rstrip() + ' [引用已过时]\n'
                        deleted_count += 1
                        log.append(f"已标记过时: {source_file}:{line_num}")
                
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
            except Exception as e:
                log.append(f"错误: {source_file} - {e}")
        
        if deleted_count > 0:
            self.scan_all_references()
            self.save_index()
        
        return deleted_count, log
    
    def check_orphaned_references(self) -> List[Dict]:
        """
        检查孤立的引用（引用了不存在的文档）
        
        Returns:
            孤立引用列表
        """
        orphaned = []
        
        # 首先建立所有实际文件的映射（用于查找缩写引用）
        ref_id_to_file: Dict[str, str] = {}
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                if not file.endswith('.md'):
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.specs_dir)
                ref_id = self.extract_ref_id_from_filename(file)
                if ref_id:
                    ref_id_to_file[ref_id] = str(rel_path)
                    # 也存储带目录的格式，如 govs/G01
                    dir_prefix = str(rel_path.parent) if rel_path.parent != Path('.') else ''
                    if dir_prefix:
                        ref_id_to_file[f"{dir_prefix}/{ref_id}"] = str(rel_path)
        
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root:
                continue
            for file in files:
                if not (file.endswith('.md') or file.endswith('.py')):
                    continue
                
                source_path = Path(root) / file
                source_rel = source_path.relative_to(self.specs_dir)
                
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    continue
                
                matches = self.CCC_DOC_PATTERN.finditer(content)
                for match in matches:
                    target_rel = match.group(0).replace('specs/', '')
                    target_path = self.specs_dir / target_rel
                    
                    # 检查是否存在（直接路径或缩写映射）
                    exists = target_path.exists()
                    if not exists:
                        # 尝试通过ref_id映射查找
                        actual_file = ref_id_to_file.get(target_rel)
                        if actual_file:
                            exists = True
                    
                    if not exists:
                        # 提取行号
                        pos = match.start()
                        line_num = content[:pos].count('\n') + 1
                        
                        orphaned.append({
                            'source_file': str(source_rel),
                            'target_file': target_rel,
                            'line_number': line_num,
                            'suggestion': f'创建文件: {target_rel}'
                        })
        
        return orphaned
    
    def generate_reference_report(self) -> str:
        """生成引用关系报告"""
        index = self.load_index()
        stats = index.get('stats', {})
        reverse_index = index.get('reverse_index', {})
        
        lines = [
            "# 文档引用关系报告",
            "",
            f"生成时间: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "## 统计信息",
            "",
            f"- 总引用数: {stats.get('total_references', 0)}",
            f"- 引用源文件数: {stats.get('total_source_files', 0)}",
            f"- 被引用目标文件数: {stats.get('total_target_files', 0)}",
            "",
            "## 被引用最多的文档（Top 10）",
            "",
        ]
        
        # 统计被引用次数
        ref_counts = [(f, len(refs)) for f, refs in reverse_index.items()]
        ref_counts.sort(key=lambda x: x[1], reverse=True)
        
        for target_file, count in ref_counts[:10]:
            target_ref_id = self.extract_ref_id_from_filename(Path(target_file).name)
            lines.append(f"- `{target_file}` ({target_ref_id or 'N/A'}): {count} 次引用")
        
        lines.extend([
            "",
            "## 孤立文档（未被引用的文档）",
            "",
        ])
        
        # 找出所有.md文件
        all_docs = set()
        referenced_docs = set(reverse_index.keys())
        
        for root, _, files in os.walk(self.specs_dir):
            if 'tools' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.md'):
                    rel_path = Path(root).relative_to(self.specs_dir) / file
                    all_docs.add(str(rel_path))
        
        orphaned_docs = all_docs - referenced_docs
        
        if orphaned_docs:
            for doc in sorted(orphaned_docs):
                lines.append(f"- `{doc}`")
        else:
            lines.append("无孤立文档")
        
        return '\n'.join(lines)


# 兼容函数接口
def build_reference_index(specs_dir: str = "specs") -> Dict:
    """构建引用索引"""
    manager = ReferenceManager(specs_dir)
    manager.scan_all_references()
    manager.save_index()
    return manager.build_reference_index()


def find_references_to(ref_id: str, specs_dir: str = "specs") -> List[Dict]:
    """查询哪些文档引用了指定编号"""
    manager = ReferenceManager(specs_dir)
    return manager.find_references_to(ref_id)


def find_references_from(ref_id: str, specs_dir: str = "specs") -> List[Dict]:
    """查询指定文档引用了哪些文档"""
    manager = ReferenceManager(specs_dir)
    return manager.find_references_from(ref_id)


def update_references(old_ref_id: str, new_ref_id: str, 
                     dry_run: bool = False, specs_dir: str = "specs") -> Tuple[int, List[str]]:
    """批量更新引用"""
    manager = ReferenceManager(specs_dir)
    return manager.update_references(old_ref_id, new_ref_id, dry_run)


def delete_references_to(ref_id: str, dry_run: bool = False, 
                        specs_dir: str = "specs") -> Tuple[int, List[str]]:
    """删除引用"""
    manager = ReferenceManager(specs_dir)
    return manager.delete_references_to(ref_id, dry_run)


def check_orphaned_references(specs_dir: str = "specs") -> List[Dict]:
    """检查孤立引用"""
    manager = ReferenceManager(specs_dir)
    return manager.check_orphaned_references()


def generate_reference_report(specs_dir: str = "specs") -> str:
    """生成引用报告"""
    manager = ReferenceManager(specs_dir)
    return manager.generate_reference_report()


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        manager = ReferenceManager()
        
        if cmd == "build":
            manager.scan_all_references()
            manager.save_index()
            print(f"引用索引已保存到: {manager.index_path}")
            
        elif cmd == "find-to" and len(sys.argv) > 2:
            refs = manager.find_references_to(sys.argv[2])
            print(f"引用了 {sys.argv[2]} 的文档:")
            for ref in refs:
                print(f"  - {ref['source_file']}:{ref['line_number']}")
                
        elif cmd == "find-from" and len(sys.argv) > 2:
            refs = manager.find_references_from(sys.argv[2])
            print(f"{sys.argv[2]} 引用了:")
            for ref in refs:
                print(f"  - {ref['target_file']}")
                
        elif cmd == "report":
            print(manager.generate_reference_report())
            
        elif cmd == "orphaned":
            orphaned = manager.check_orphaned_references()
            print(f"发现 {len(orphaned)} 个孤立引用:")
            for item in orphaned:
                print(f"  - {item['source_file']}:{item['line_number']} -> {item['target_file']}")
