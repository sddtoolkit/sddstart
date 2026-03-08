"""
文档编码规范校验器。

[SDD Traceability]
- Standard: S01 (文档编码规范)

## 规范引用

本检查器实现以下规范的校验逻辑：

| 规范文档 | 引用编号 | 适用章节 |
|----------|----------|----------|
| 文档编码规范 | S01 | 全文 |

### S01-文档编码规范 要求
- 编码组成：`<前缀>-<编码段>-<SLUG>.md`
- 前缀类型：RQ（需求）、DS（设计）、TK（任务）、ADR（决策）、G（治理）、S（标准）
- 分隔符规范：唯一分隔符 `-`，禁止下划线、空格
- NN码规则：01-99 或 AA-ZZ（排除 O、I、L）
- CCC码区间：100-999，按技术层划分
- 例外文件：README.md、INDEX.md、主文档文件不受规范限制

## 实现映射

| 方法 | 规范要求 | 规范章节 |
|------|----------|----------|
| `VALID_PREFIXES` | 六类文档前缀定义 | S01-1.2 编码组成 |
| `CCC_RANGES` | CCC码分类区间 | S01-5.1 CCC码 |
| `_check_rq_ds_adr()` | RQ/DS/ADR 格式校验 | S01-3.1~3.4 |
| `_check_tk()` | TK 格式校验（含YYWW） | S01-3.3 |
| `_check_gov_std()` | G/S 格式校验 | S01-3.5~3.6 |
| `extract_reference_id()` | 引用编号提取 | S01-2.1 引用编号定义 |

参见：
- specs/standards/S01-文档编码规范.md
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional


class DocumentCodingChecker:
    """
    文档编码规范校验器。

    规范引用：S01-文档编码规范

    功能：
    1. 校验六类文档（RQ/DS/TK/ADR/G/S）的编码格式
    2. 检查引用编号唯一性
    3. 提供文档定位和重命名功能
    4. 校验 CCC 码和 NN 码有效性

    支持的文档类型（S01-3.x）：
    - RQ: 需求文档，格式 `RQ-<CCC><NN>-<SLUG>需求.md`
    - DS: 设计文档，格式 `DS-<CCC><NN>-<SLUG>设计.md`
    - TK: 任务文档，格式 `TK-<CCC><YYWW><NN>-<SLUG>任务.md`
    - ADR: 决策文档，格式 `ADR-<CCC><NN>-<SLUG>决策.md`
    - G: 治理文档，格式 `G<NN>-<SLUG>.md`
    - S: 标准文档，格式 `S<NN>-<SLUG>.md`
    """

    # 规范引用：S01-1.2 编码组成 - 六类文档前缀
    VALID_PREFIXES = ['RQ', 'DS', 'TK', 'ADR', 'G', 'S']

    # 规范引用：S01-5.2 NN码 - 排除易混淆字母 O、I、L
    EXCLUDED_LETTERS = {'O', 'I', 'L'}
    VALID_LETTERS = set('ABCDEFGHJKMNPQRSTUVWXYZ')  # 23 个可用字母

    # 规范引用：S01-5.1 CCC码分类表
    CCC_RANGES = {
        'core': (100, 199),        # 项目核心层
        'frontend': (200, 299),    # 前端技术层
        'business': (300, 399),    # 业务领域层
        'backend': (400, 499),     # 后端技术层
        'data': (500, 599),        # 数据层
        'component': (600, 699),   # 组件/工具层
        'special': (700, 799),     # 专项技术层
        'reserved': (800, 899),    # 预留扩展
        'ops': (900, 999),         # 运维支撑层
    }

    def __init__(self, specs_dir: str = "specs"):
        self.specs_dir = Path(specs_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def check_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        校验所有文档

        Returns:
            (是否通过，错误列表，警告列表)
        """
        self.errors = []
        self.warnings = []

        # 收集所有引用编号，用于唯一性校验
        ref_ids: dict[str, str] = {}

        for root, dirs, files in os.walk(self.specs_dir):
            # 跳过工具目录和测试目录
            if 'tools' in root or '__pycache__' in root:
                continue

            for file in files:
                if not file.endswith('.md'):
                    continue

                filepath = Path(root) / file
                rel_path = filepath.relative_to(self.specs_dir)

                # 校验文档编码
                is_valid, error = self._check_document(file, rel_path)

                if not is_valid:
                    self.errors.append(f"{rel_path}: {error}")
                    continue

                # 提取引用编号并检查唯一性
                ref_id = self.extract_reference_id(file)
                if ref_id:
                    if ref_id in ref_ids:
                        self.errors.append(
                            f"{rel_path}: 引用编号重复 '{ref_id}' "
                            f"(已存在于 {ref_ids[ref_id]})"
                        )
                    else:
                        ref_ids[ref_id] = str(rel_path)

        return len(self.errors) == 0, self.errors, self.warnings

    def _check_document(self, filename: str, rel_path: Path) -> Tuple[bool, Optional[str]]:
        """
        校验单个文档

        Returns:
            (是否通过，错误信息)
        """
        # 例外文件：README.md 和 INDEX.md 不受文档编码规范限制
        if filename in ('README.md', 'INDEX.md'):
            return True, None

        # 主文档例外：允许核心目录下的主文档使用简化命名
        # 这些是项目基线文档，不强制重命名
        main_doc_exceptions = {
            '1-reqs/requirements.md',
            '2-designs/architecture.md',
            '3-tasks/task-plan.md',
            'tests/test-plan.md',
            'releases/release-plan.md',
            'runbook/runbook.md',
            'changelogs/CHANGELOG.md',
        }
        str_path = str(rel_path)
        if str_path in main_doc_exceptions:
            return True, None

        # 首先解析文件名，判断是否使用 CCC 编码体系
        parts = filename.replace('.md', '').split('-')

        # 检查是否使用 CCC 编码前缀
        prefix = parts[0] if parts else ""

        # 特殊处理 G 和 S 前缀（如 G01, S01）
        # 提取前缀类型：G01 → G, S01 → S, RQ-10102 → RQ
        if prefix.startswith('G'):
            prefix_type = 'G'
        elif prefix.startswith('S'):
            prefix_type = 'S'
        else:
            prefix_type = prefix

        # 检查核心目录是否必须使用规范命名
        strict_naming_dirs = {
            '1-reqs/': 'RQ',
            '2-designs/': 'DS',
            '3-tasks/': 'TK',
            'adrs/': 'ADR',
        }
        for dir_prefix, expected_doc_prefix in strict_naming_dirs.items():
            if str_path.startswith(dir_prefix):
                if prefix_type != expected_doc_prefix:
                    return False, f"目录 '{dir_prefix}' 下的文档必须使用 '{expected_doc_prefix}' 前缀，实际为 '{prefix}'"

        # 如果不是六类文档前缀，使用传统命名检查
        if prefix_type not in self.VALID_PREFIXES:
            return self._check_traditional_naming(filename)

        # 使用 CCC 编码体系的文档，进行严格检查
        # 检查分隔符（只能使用减号）
        if '_' in filename:
            return False, "包含下划线'_'，只允许使用减号'-'"

        # 检查空格
        if ' ' in filename:
            return False, "包含空格，不允许"

        if len(parts) < 2:
            return False, "格式错误，至少需要前缀和 SLUG"

        # 根据前缀进行专项校验
        if prefix_type in ['RQ', 'DS', 'ADR']:
            return self._check_rq_ds_adr(filename, parts)
        elif prefix_type == 'TK':
            return self._check_tk(filename, parts)
        elif prefix_type in ['G', 'S']:
            return self._check_gov_std(filename, parts)

        return True, None

    def _check_traditional_naming(self, filename: str) -> Tuple[bool, Optional[str]]:
        """校验传统命名（非六类文档：templates、examples、agents、skills、tools 等）"""
        # 特殊允许的特例文件
        special_allowed = {
            'README.md', 'CHANGELOG.md', 'index.md', 'sources.md',
            'traceability.md', 'capability-matrix.md', 'agents.md',
            'skills.md', 'tools.md', 'user-guide.md', 'readme.md',
            'requirements.md', 'architecture.md', 'task-plan.md',
            'test-plan.md', 'release-plan.md', 'runbook.md',
        }

        name_without_ext = filename.replace('.md', '')
        if filename in special_allowed or name_without_ext in special_allowed:
            return True, None

        # 模板文件、示例文件使用小写英文、数字、减号、点
        if re.match(r'^[a-z0-9\-\.]+\.md$', filename):
            # 检查禁止的无语义文件名
            banned_names = {'final', 'new', 'temp', 'tmp', 'draft'}
            if name_without_ext.lower() in banned_names:
                return False, f"禁止的无语义文件名 '{filename}'"
            return True, None

        # 允许带有 README 的文件
        if 'README' in filename:
            return True, None

        return False, "传统命名只允许小写英文、数字、减号、点"

    def _check_rq_ds_adr(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        校验 RQ/DS/ADR 格式：<PREFIX>-<CCC><NN>-<SLUG>后缀.md
        示例：RQ-10102-用户注册需求.md
        """
        prefix = parts[0]

        # 检查格式：至少 3 段（前缀 - 编码-SLUG...）
        if len(parts) < 3:
            return False, f"格式错误，应为 {prefix}-<CCC><NN>-<SLUG>后缀.md"

        # 检查编码段
        code_segment = parts[1]
        if len(code_segment) < 5:
            return False, f"编码段长度错误，应为 5 位以上，实际{len(code_segment)}位"

        # 提取 CCC (前 3 位)
        ccc_str = code_segment[:3]
        if not ccc_str.isdigit():
            return False, f"CCC 码必须是 3 位数字，实际'{ccc_str}'"

        ccc = int(ccc_str)
        if not (100 <= ccc <= 999):
            return False, f"CCC 码必须在 100-999 之间，实际{ccc}"

        # 提取 NN (第 4-5 位)
        nn_str = code_segment[3:5]
        if not self._is_valid_nn(nn_str):
            return False, f"NN 码格式错误，应为 01-99 或 AA-ZZ(排除 O,I,L)，实际'{nn_str}'"

        # 检查 SLUG 非空
        slug_parts = parts[2:]
        if not slug_parts or all(not p for p in slug_parts):
            return False, "SLUG 不能为空"

        # 检查后缀
        suffix_map = {'RQ': '需求', 'DS': '设计', 'ADR': '决策'}
        expected_suffix = suffix_map.get(prefix)
        if expected_suffix and not filename.endswith(f'{expected_suffix}.md'):
            return False, f"后缀错误，应以'{expected_suffix}.md'结尾"

        return True, None

    def _check_tk(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        校验 TK 格式：TK-<CCC><YYWW><NN>-<SLUG>任务.md
        示例：TK-201260901-前端页面开发任务.md
        """
        if len(parts) < 3:
            return False, "格式错误，应为 TK-<CCC><YYWW><NN>-<SLUG>任务.md"

        # 检查编码段
        code_segment = parts[1]
        if len(code_segment) < 9:
            return False, f"编码段长度错误，应为 9 位，实际{len(code_segment)}位"

        # 提取 CCC (前 3 位)
        ccc_str = code_segment[:3]
        if not ccc_str.isdigit():
            return False, f"CCC 码必须是 3 位数字，实际'{ccc_str}'"

        ccc = int(ccc_str)
        if not (100 <= ccc <= 999):
            return False, f"CCC 码必须在 100-999 之间，实际{ccc}"

        # 提取 YYWW (第 4-7 位)
        yyww_str = code_segment[3:7]
        if not yyww_str.isdigit():
            return False, f"YYWW 码必须是 4 位数字，实际'{yyww_str}'"

        yy_val = int(yyww_str[:2])  # noqa: F841
        ww = int(yyww_str[2:])
        if not (1 <= ww <= 53):
            return False, f"周数必须在 01-53 之间，实际{ww}"

        # 提取 NN (第 8-9 位)
        nn_str = code_segment[7:9]
        if not self._is_valid_nn(nn_str):
            return False, f"NN 码格式错误，应为 01-99 或 AA-ZZ(排除 O,I,L)，实际'{nn_str}'"

        # 检查后缀
        if not filename.endswith('任务.md'):
            return False, "后缀错误，应以'任务.md'结尾"

        return True, None

    def _check_gov_std(self, filename: str, parts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        校验 G/S 格式：<PREFIX><NN>-<SLUG>.md
        示例：G01-项目宪章.md, S01-文档编码规范.md
        """
        # parts[0] 包含前缀和 NN，如 'G01' 或 'S01'
        prefix_with_nn = parts[0]

        # 提取前缀类型和 NN 码
        if prefix_with_nn.startswith('G'):
            prefix_type = 'G'
            nn_str = prefix_with_nn[1:]  # G01 → 01
        elif prefix_with_nn.startswith('S'):
            prefix_type = 'S'
            nn_str = prefix_with_nn[1:]  # S01 → 01
        else:
            return False, f"未知的前缀类型：{prefix_with_nn}"

        # 检查 NN 码
        if not nn_str:
            return False, f"格式错误，{prefix_type}后面应跟 NN 码"

        if not self._is_valid_nn(nn_str):
            return False, f"NN 码格式错误，应为 01-99 或 AA-ZZ(排除 O,I,L)，实际'{nn_str}'"

        # 检查 SLUG 非空（parts[1] 及之后都是 SLUG）
        if len(parts) < 2:
            return False, f"格式错误，应为 {prefix_type}<NN>-<SLUG>.md"

        slug = '-'.join(parts[1:])
        if not slug:
            return False, "SLUG 不能为空"

        # 检查 SLUG 长度（建议 4-15 个字符）
        if len(slug) > 30:
            self.warnings.append(f"SLUG 过长 ({len(slug)}字符)，建议控制在 15 字以内")

        return True, None

    def _is_valid_nn(self, nn_str: str) -> bool:
        """
        校验 NN 码是否有效
        格式：01-99 或 AA-ZZ(排除 O,I,L)
        """
        if len(nn_str) != 2:
            return False

        # 数字形式
        if nn_str.isdigit():
            num = int(nn_str)
            return 1 <= num <= 99

        # 字母形式
        if nn_str.isalpha() and nn_str.isupper():
            return all(c in self.VALID_LETTERS for c in nn_str)

        return False

    def extract_reference_id(self, filename: str) -> Optional[str]:
        """
        从文件名提取引用编号

        Returns:
            引用编号，无法提取返回 None
        """
        if not filename.endswith('.md'):
            return None

        name = filename[:-3]  # 去掉.md
        parts = name.split('-')

        if len(parts) < 2:
            return None

        prefix = parts[0]

        if prefix in ['RQ', 'DS', 'ADR']:
            # RQ-10102-用户注册需求 → RQ-10102
            if len(parts) >= 3 and len(parts[1]) >= 5:
                return f"{parts[0]}-{parts[1][:5]}"
            return None
        elif prefix == 'TK':
            # TK-201260901-前端页面开发任务 → TK-201260901
            if len(parts) >= 3 and len(parts[1]) >= 9:
                return f"{parts[0]}-{parts[1][:9]}"
            return None
        elif prefix in ['G', 'S']:
            # G01-项目宪章 → G01
            # S01-文档编码规范 → S01
            if len(parts) >= 2:
                return f"{parts[0]}-{parts[1]}"
            return None

        return None

    def locate_document(self, ref_id: str) -> Tuple[Optional[Path], Optional[str], List[Path]]:
        """委托给统一实现定位文档。"""
        return resolve_spec_path(ref_id)

    def validate_ccc(self, ccc: int) -> Tuple[bool, str]:
        """
        校验 CCC 码并返回分类描述

        Returns:
            (是否有效，分类描述)
        """
        if not (100 <= ccc <= 999):
            return False, "CCC 码必须在 100-999 之间"

        for category, (start, end) in self.CCC_RANGES.items():
            if start <= ccc <= end:
                descriptions = {
                    'core': '项目核心层',
                    'frontend': '前端技术层',
                    'business': '业务领域层',
                    'backend': '后端技术层',
                    'data': '数据层',
                    'component': '组件/工具层',
                    'special': '专项技术层',
                    'reserved': '预留扩展',
                    'ops': '运维支撑层',
                }
                return True, descriptions.get(category, '未知分类')

        return False, "未知分类"

    def suggest_nn(self, ccc: int, existing_docs: List[str]) -> str:
        """
        建议下一个可用的 NN 码

        Args:
            ccc: CCC 分类码
            existing_docs: 该 CCC 下已存在的文档列表

        Returns:
            建议的 NN 码
        """
        used_nns = set()

        for doc in existing_docs:
            ref_id = self.extract_reference_id(doc)
            if ref_id:
                # 提取 NN 部分
                parts = ref_id.split('-')
                if len(parts) >= 2 and len(parts[1]) >= 5:
                    nn = parts[1][3:5] if parts[0] in ['RQ', 'DS', 'ADR'] else parts[1][7:9]
                    used_nns.add(nn)

        # 查找最小的可用 NN
        for i in range(1, 100):
            nn = f"{i:02d}"
            if nn not in used_nns:
                return nn

        # 数字用完，使用字母
        for c1 in self.VALID_LETTERS:
            for c2 in self.VALID_LETTERS:
                nn = c1 + c2
                if nn not in used_nns:
                    return nn

        return "ZZ"  # 理论上不会到达


def main():
    """命令行入口"""
    import sys

    specs_dir = sys.argv[1] if len(sys.argv) > 1 else "specs"

    checker = DocumentCodingChecker(specs_dir)
    passed, errors, warnings = checker.check_all()

    print(f"\n{'='*60}")
    print("文档编码规范检查结果")
    print(f"{'='*60}")

    if passed and not errors:
        print("✅ 所有文档符合编码规范")
    else:
        print(f"❌ 发现 {len(errors)} 个错误")
        for error in errors:
            print(f"   - {error}")

    if warnings:
        print(f"\n⚠️ 发现 {len(warnings)} 个警告")
        for warning in warnings:
            print(f"   - {warning}")

    print(f"{'='*60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    exit(main())
