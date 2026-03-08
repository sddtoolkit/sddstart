"""
CLI 子命令注册器。

## 觌范引用
本模块定义 sddtool.py 的所有 CLI 子命令
与 CLI 命令的对应关系：

| 命令类别 | 对应检查器/生成器 |
|--------|-------------------|
| check-* | 对应 checkers/*checker.py |
| create-* | 对应文档模板创建 |
| generate-* | 对应 generators/*.py |
| locate/read/trace | 文档定位与追踪 |
| reference-* | 引用关系管理 |

## 命令分组

### 初始化与生成
- initialize: 初始化 specs 目录
- generate-index: 生成索引
- generate-traceability-matrix: 生成追溯矩阵
- generate-agent-dispatch: 生成调度规则
- generate-tool-adapters: 生成工具适配

### 文档创建
- create-requirement: 创建需求文档
- create-design: 创建设计文档
- create-adr: 创建 ADR 文档
- create-task: 创建任务文档
- create-test: 创建测试文档
- create-release: 创建发布文档

### 规范检查
- check-status: 检查完整性
- check-naming: 检查命名规范
- check-document-coding: 检查文档编码
- check-completeness: 检查追溯完整性
- check-governance: 检查治理审批
- check-dependencies: 检查依赖风险
- check-code-quality: 检查代码质量
- check-drift: 检查规范漂移
- validate-requirement: 校验需求文档
- validate-design: 校验设计文档
- check-changelog: 检查变更日志

### 文档操作
- locate-document: 定位文档
- read-document: 读取文档
- trace-dependencies: 追踪依赖
- rename-document: 重命名文档

### 引用管理
- build-reference-index: 构建引用索引
- find-references-to: 查询引用目标
- find-references-from: 查询引用来源
- update-references: 更新引用
- delete-references: 删除引用
- check-orphaned-references: 检查孤立引用
- reference-report: 生成引用报告

### 调度与工具
- resolve-agent-dispatch: 解析调度建议
- list-tool-adapters: 列出工具适配
- add-tool-adapter: 添加工具适配
- remove-tool-adapter: 移除工具适配
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from sdd.generators.tooladaptergenerator import SUPPORTED_ENTRY_FORMATS

# 命令处理函数类型定义
CommandHandler = Callable[[argparse.Namespace], int]


def _requiring_handler(handlers: dict[str, CommandHandler], key: str) -> CommandHandler:
    """
    读取并校验命令处理函数映射。

    Args:
        handlers: 命令处理函数映射
        key: 命令键名

    Returns:
        CommandHandler: 对应的处理函数

    Raises:
        KeyError: 缺少必需的处理函数
    """
    """读取并校验命令处理函数映射。"""
    try:
        return handlers[key]
    except KeyError as exc:
        raise KeyError(f"缺少命令处理函数：{key}") from exc


def register_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, CommandHandler]) -> None:
    """向解析器注册全部 CLI 子命令。"""
    version_cmd = subparsers.add_parser("version", help="显示 SDD 体系与工具版本号")
    version_cmd.set_defaults(running=_requiring_handler(handlers, "version"))

    init_cmd = subparsers.add_parser("initialize", help="初始化或补齐 specs 目录")
    init_cmd.set_defaults(running=_requiring_handler(handlers, "initialize"))

    gen_cmd = subparsers.add_parser("generate-index", help="生成 specs 索引")
    gen_cmd.set_defaults(running=_requiring_handler(handlers, "generate-index"))

    trace_cmd = subparsers.add_parser(
        "generate-traceability-matrix",
        help="生成追溯矩阵（md/json）",
    )
    trace_cmd.set_defaults(running=_requiring_handler(handlers, "generate-traceability-matrix"))

    agent_dispatch_cmd = subparsers.add_parser(
        "generate-agent-dispatch",
        help="生成 Agent/Skill 统一调度规则",
    )
    agent_dispatch_cmd.set_defaults(running=_requiring_handler(handlers, "generate-agent-dispatch"))

    tool_adapters_cmd = subparsers.add_parser(
        "generate-tool-adapters",
        help="生成/同步多工具入口与适配清单",
    )
    tool_adapters_cmd.set_defaults(running=_requiring_handler(handlers, "generate-tool-adapters"))

    req_cmd = subparsers.add_parser("create-requirement", help="创建需求文档")
    req_cmd.add_argument("slug", nargs="?", help="需求简短描述（中文SLUG）")
    req_cmd.add_argument("--ccc", help="3位分类码（默认从项目简介推理）")
    req_cmd.add_argument("--nn", help="2位顺序码（默认自动递增）")
    req_cmd.add_argument("--intro", help="项目简介，用于推理 CCC 码")
    req_cmd.set_defaults(running=_requiring_handler(handlers, "create-requirement"))

    design_cmd = subparsers.add_parser("create-design", help="创建设计文档")
    design_cmd.add_argument("slug", nargs="?", help="设计简短描述（中文SLUG）")
    design_cmd.add_argument("--ccc", help="3位分类码（默认从项目简介推理）")
    design_cmd.add_argument("--nn", help="2位顺序码（默认自动递增）")
    design_cmd.add_argument("--intro", help="项目简介，用于推理 CCC 码")
    design_cmd.set_defaults(running=_requiring_handler(handlers, "create-design"))

    adr_cmd = subparsers.add_parser("create-adr", help="创建 ADR")
    adr_cmd.add_argument("slug", help="决策简短描述（中文SLUG）")
    adr_cmd.add_argument("--ccc", help="3位分类码（默认从项目简介推理）")
    adr_cmd.add_argument("--nn", help="2位顺序码（默认自动递增）")
    adr_cmd.add_argument("--intro", help="项目简介，用于推理 CCC 码")
    adr_cmd.set_defaults(running=_requiring_handler(handlers, "create-adr"))

    task_cmd = subparsers.add_parser("create-task", help="创建任务文档")
    task_cmd.add_argument("slug", help="任务简短描述（中文SLUG）")
    task_cmd.add_argument("--ccc", help="3位分类码（默认从项目简介推理）")
    task_cmd.add_argument("--nn", help="2位顺序码（默认自动递增）")
    task_cmd.add_argument("--intro", help="项目简介，用于推理 CCC 码")
    task_cmd.set_defaults(running=_requiring_handler(handlers, "create-task"))

    test_cmd = subparsers.add_parser("create-test", help="创建测试文档")
    test_cmd.add_argument("scope", help="范围")
    test_cmd.add_argument("test_id", help="测试 ID")
    test_cmd.set_defaults(running=_requiring_handler(handlers, "create-test"))

    release_cmd = subparsers.add_parser("create-release", help="创建发布文档")
    release_cmd.add_argument("version", help="版本号")
    release_cmd.set_defaults(running=_requiring_handler(handlers, "create-release"))

    status_cmd = subparsers.add_parser("check-status", help="检查 spec 完整性")
    status_cmd.set_defaults(running=_requiring_handler(handlers, "check-status"))

    gates_cmd = subparsers.add_parser("check-quality-gates", help="执行全量质量门禁检查（命名/漂移/完备性）")
    gates_cmd.set_defaults(running=_requiring_handler(handlers, "check-quality-gates"))

    req_val_cmd = subparsers.add_parser(
        "validate-requirement",
        help="检查需求文档",
    )
    req_val_cmd.set_defaults(running=_requiring_handler(handlers, "validate-requirement"))

    design_val_cmd = subparsers.add_parser("validate-design", help="检查设计文档")
    design_val_cmd.set_defaults(running=_requiring_handler(handlers, "validate-design"))

    changelog_cmd = subparsers.add_parser("check-changelog", help="检查变更日志")
    changelog_cmd.set_defaults(running=_requiring_handler(handlers, "check-changelog"))

    governance_cmd = subparsers.add_parser(
        "check-governance",
        help="检查治理审批链字段",
    )
    governance_cmd.set_defaults(running=_requiring_handler(handlers, "check-governance"))

    dep_cmd = subparsers.add_parser(
        "check-dependencies",
        help="检查依赖风险与可复现性",
    )
    dep_cmd.set_defaults(running=_requiring_handler(handlers, "check-dependencies"))

    quality_cmd = subparsers.add_parser(
        "check-code-quality",
        help="检查代码静态质量信号",
    )
    quality_cmd.set_defaults(running=_requiring_handler(handlers, "check-code-quality"))

    complete_cmd = subparsers.add_parser(
        "check-completeness",
        help="检查需求到测试链路完整性",
    )
    complete_cmd.set_defaults(running=_requiring_handler(handlers, "check-completeness"))

    naming_cmd = subparsers.add_parser("check-naming", help="检查命名与索引登记")
    naming_cmd.set_defaults(running=_requiring_handler(handlers, "check-naming"))

    # 上下文聚合命令
    bundle_cmd = subparsers.add_parser("bundle-task-context", help="聚合任务关联的 REQ/DSN/ADR 上下文到 tmp/")
    bundle_cmd.add_argument("task_id", help="任务 ID，如 TK-101260901")
    bundle_cmd.set_defaults(running=_requiring_handler(handlers, "bundle-task-context"))

    trace_code_cmd = subparsers.add_parser("trace-code", help="从代码文件反向追溯规范来源")
    trace_code_cmd.add_argument("file_path", help="代码文件路径")
    trace_code_cmd.set_defaults(running=_requiring_handler(handlers, "trace-code"))

    doc_coding_cmd = subparsers.add_parser(
        "check-document-coding",
        help="检查文档编码规范（CCC-NN-YYWW体系）",
    )
    doc_coding_cmd.set_defaults(running=_requiring_handler(handlers, "check-document-coding"))

    locate_doc_cmd = subparsers.add_parser(
        "locate-document",
        help="根据文档编号定位文档路径",
    )
    locate_doc_cmd.add_argument("ref_id", help="文档编号，如 RQ-10102, G01, S01")
    locate_doc_cmd.set_defaults(running=_requiring_handler(handlers, "locate-document"))

    read_doc_cmd = subparsers.add_parser(
        "read-document",
        help="根据文档编号读取文档内容",
    )
    read_doc_cmd.add_argument("ref_id", help="文档编号，如 RQ-10102, G01, S01")
    read_doc_cmd.set_defaults(running=_requiring_handler(handlers, "read-document"))

    trace_deps_cmd = subparsers.add_parser(
        "trace-dependencies",
        help="追踪文档依赖关系（关联的需求、设计、任务、代码）",
    )
    trace_deps_cmd.add_argument("ref_id", help="文档编号，如 RQ-10102, DS-20101")
    trace_deps_cmd.add_argument("--json", action="store_true", dest="as_json", help="以 JSON 格式输出")
    trace_deps_cmd.set_defaults(running=_requiring_handler(handlers, "trace-dependencies"))

    rename_doc_cmd = subparsers.add_parser(
        "rename-document",
        help="更换文档编号",
    )
    rename_doc_cmd.add_argument(
        "old_identifier",
        help="旧文件名（完整）或文档编号（如 RQ-10102）。使用文档编号时需配合 --by-ref-id 选项",
    )
    rename_doc_cmd.add_argument("new_filename", help="新文件名（完整，如 RQ-10103-用户注册需求.md）")
    rename_doc_cmd.add_argument(
        "--by-ref-id",
        action="store_true",
        help="将 old_identifier 解释为文档编号而非文件名",
    )
    rename_doc_cmd.set_defaults(running=_requiring_handler(handlers, "rename-document"))

    drift_cmd = subparsers.add_parser("check-drift", help="检查实现与规范来源标记")
    drift_cmd.set_defaults(running=_requiring_handler(handlers, "check-drift"))

    list_tool_adapters_cmd = subparsers.add_parser(
        "list-tool-adapters",
        help="列出工具适配清单",
    )
    list_tool_adapters_cmd.set_defaults(running=_requiring_handler(handlers, "list-tool-adapters"))

    add_tool_adapter_cmd = subparsers.add_parser(
        "add-tool-adapter",
        help="新增工具适配定义",
    )
    add_tool_adapter_cmd.add_argument("tool_id", help="工具 ID（如 opencode）")
    add_tool_adapter_cmd.add_argument("display_name", help="工具展示名")
    add_tool_adapter_cmd.add_argument("--entry-file", required=True, help="入口文件路径（相对仓库根目录）")
    add_tool_adapter_cmd.add_argument(
        "--entry-format",
        default="markdown",
        choices=sorted(SUPPORTED_ENTRY_FORMATS),
        help="入口文件格式",
    )
    add_tool_adapter_cmd.add_argument("--shared-entry", action="store_true", help="入口文件是否共享")
    add_tool_adapter_cmd.add_argument(
        "--extra-entry",
        action="append",
        help="附加入口，格式 path:format，可重复",
    )
    add_tool_adapter_cmd.set_defaults(running=_requiring_handler(handlers, "add-tool-adapter"))

    remove_tool_adapter_cmd = subparsers.add_parser(
        "remove-tool-adapter",
        help="移除工具适配定义并按需回收空入口文件",
    )
    remove_tool_adapter_cmd.add_argument("tool_id", help="工具 ID")
    remove_tool_adapter_cmd.set_defaults(running=_requiring_handler(handlers, "remove-tool-adapter"))

    resolve_dispatch_cmd = subparsers.add_parser(
        "resolve-agent-dispatch",
        help="根据 Agent/Skill 定义解析任务调度建议",
    )
    resolve_dispatch_cmd.add_argument("--task", required=True, help="任务描述")
    resolve_dispatch_cmd.add_argument("--stage", help="阶段（可选）")
    resolve_dispatch_cmd.add_argument("--skills", action="append", help="指定 Skill（可多次）")
    resolve_dispatch_cmd.add_argument("--json", action="store_true", dest="as_json", help="以 JSON 输出结果")
    resolve_dispatch_cmd.set_defaults(running=_requiring_handler(handlers, "resolve-agent-dispatch"))

    # 引用关系管理命令
    ref_build_cmd = subparsers.add_parser(
        "build-reference-index",
        help="构建文档引用关系索引",
    )
    ref_build_cmd.set_defaults(running=_requiring_handler(handlers, "build-reference-index"))

    ref_find_to_cmd = subparsers.add_parser(
        "find-references-to",
        help="查询哪些文档引用了指定编号",
    )
    ref_find_to_cmd.add_argument("ref_id", help="文档编号，如 G01, S01, RQ-10102")
    ref_find_to_cmd.set_defaults(running=_requiring_handler(handlers, "find-references-to"))

    ref_find_from_cmd = subparsers.add_parser(
        "find-references-from",
        help="查询指定文档引用了哪些文档",
    )
    ref_find_from_cmd.add_argument("ref_id", help="文档编号")
    ref_find_from_cmd.set_defaults(running=_requiring_handler(handlers, "find-references-from"))

    ref_update_cmd = subparsers.add_parser(
        "update-references",
        help="批量更新引用关系",
    )
    ref_update_cmd.add_argument("old_ref_id", help="旧引用编号")
    ref_update_cmd.add_argument("new_ref_id", help="新引用编号")
    ref_update_cmd.add_argument("--dry-run", action="store_true", help="仅预览，不实际修改")
    ref_update_cmd.set_defaults(running=_requiring_handler(handlers, "update-references"))

    ref_delete_cmd = subparsers.add_parser(
        "delete-references",
        help="删除对指定文档的引用",
    )
    ref_delete_cmd.add_argument("ref_id", help="要删除引用的文档编号")
    ref_delete_cmd.add_argument("--dry-run", action="store_true", help="仅预览")
    ref_delete_cmd.set_defaults(running=_requiring_handler(handlers, "delete-references"))

    ref_orphaned_cmd = subparsers.add_parser(
        "check-orphaned-references",
        help="检查孤立的引用（引用了不存在的文档）",
    )
    ref_orphaned_cmd.set_defaults(running=_requiring_handler(handlers, "check-orphaned-references"))

    ref_report_cmd = subparsers.add_parser(
        "reference-report",
        help="生成文档引用关系报告",
    )
    ref_report_cmd.set_defaults(running=_requiring_handler(handlers, "reference-report"))
