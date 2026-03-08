from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from collections.abc import Callable
from pathlib import Path

# --- 核心配置与 IO ---
from sdd.config import (
    BANNED_NAMES, CATEGORY_DIRECTORY_ROWS, DIRECTORIES, REPO_ROOT,
    REQUIRED_SPEC_FILES, SEED_CONTENTS, SPECIAL_MARKDOWN_NAMES,
    SPECS_DIR, SPEC_MARK, SUPPORTED_CODE_SUFFIXES, TEMPLATE_CONTENTS
)
from sdd.io import read_text_safe, check_file_integrity
from sdd.log import log_error, log_info, log_warning

# --- 通用工具 ---
from sdd.utils import (
    copy_template, get_current_date_slug, get_next_nn,
    get_yyww, normalize_id, normalize_md_token,
    read_first_heading, resolve_spec_path, validate_semver,
    validate_slug as validating_slug_value, write_file_safe,
    check_structured_bullets, count_specs_by_dir,
    ensure_gov_metadata, extract_registered_ids,
    list_files_depth_two, list_top_directories
)

# --- 校验器 (Checkers) ---
from sdd.checkers.completenesschecker import check_completeness
from sdd.checkers.dependencychecker import check_dependencies
from sdd.checkers.documentcodingchecker import DocumentCodingChecker
from sdd.checkers.driftchecker import check_spec_drift as check_drift_files
from sdd.checkers.namingchecker import NamingChecker, is_ccc_coded
from sdd.checkers.qualitychecker import check_code_quality

# --- 生成器 (Generators) ---
from sdd.generators.agentdispatchgenerator import (
    build_agent_dispatch_payload, resolve_agent_dispatch, write_agent_dispatch_file
)
from sdd.generators.changeloggenerator import check_changelog_file
from sdd.generators.dependencytracer import trace_dependencies
from sdd.generators.indexgenerator import write_index
from sdd.generators.tooladaptergenerator import (
    MANIFEST_REL_PATH, add_tool_adapter, delete_entry_files,
    list_tool_adapters, load_tool_adapter_manifest,
    remove_tool_adapter, sync_tool_adapter_entries,
    write_tool_adapter_manifest
)
from sdd.generators.traceabilitygenerator import generate_traceability_outputs

# --- 验证器 (Validators) ---
from sdd.validators.designvalidator import check_design_file
from sdd.validators.reqvalidator import check_requirement_file
from sdd.validators.sectionvalidator import check_required_nonempty_bullets
from sdd.validators.speccompliance import check_required_files

from .commandhandlers import CommandHandler, build_handler_map

def refresh_index_after_change() -> int:
    """在文档变更后刷新索引登记。"""
    # Keep index registration in sync with newly created spec files.
    return generate_index(argparse.Namespace())


def _create_from_template(template_rel: str, target_rel: str) -> int:
    """复用的文档创建流程：拷贝模板并刷新索引。"""
    success = copy_template(template_rel, target_rel)
    if not success:
        return 1
    return refresh_index_after_change()


def _resolve_optional_slug_target(
    raw_name: str | None,
    field_name: str,
    default_target: str,
    named_target_builder: Callable[[str], str],
) -> str | None:
    """解析可选名称参数并生成目标路径。"""
    if not raw_name:
        return default_target

    slug = validating_slug_value(raw_name, field_name)
    if slug is None:
        return None
    return named_target_builder(slug)


def _infer_ccc_from_text(text: str, prefix: str) -> str:
    """根据文本内容推理 CCC 码。"""
    text = text.lower()
    
    # 关键词映射
    mapping = {
        "101": ["项目", "总纲", "治理", "规范", "宪章", "架构", "体系", "流程"],
        "201": ["前端", "web", "react", "vue", "小程序", "app", "移动", "界面", "ui"],
        "301": ["用户", "业务", "订单", "支付", "商品", "领域", "营销", "内容", "社交"],
        "401": ["后端", "网关", "api", "服务", "bff", "微服务", "消息队列", "缓存"],
        "501": ["数据", "数据库", "mysql", "postgresql", "nosql", "redis", "仓库"],
        "601": ["组件", "工具", "库", "框架", "脚手架"],
        "701": ["ai", "人工智能", "机器学习", "区块链", "游戏", "嵌入式"],
        "901": ["运维", "部署", "监控", "ci/cd", "docker", "k8s", "流水线", "环境"]
    }
    
    # 根据前缀和关键词进行简单权重计算
    best_ccc = None
    max_matches = 0
    
    for ccc, keywords in mapping.items():
        matches = sum(1 for k in keywords if k in text)
        if matches > max_matches:
            max_matches = matches
            best_ccc = ccc
            
    if best_ccc:
        return best_ccc
        
    # 默认值回退
    default_map = {
        "RQ": "101",
        "DS": "201",
        "ADR": "101",
        "TK": "201"
    }
    return default_map.get(prefix, "101")


def _resolve_ccc(args: argparse.Namespace, prefix: str) -> str:
    """解析 CCC 码，如果未提供则从项目简介推理。"""
    if args.ccc:
        return args.ccc
        
    intro_text = ""
    
    # 1. 检查命令行提供的 --intro
    if hasattr(args, "intro") and args.intro:
        intro_text = args.intro
    else:
        # 2. 检查项目中的基线文件
        intro_files = [
            SPECS_DIR / "govs/G02-项目宪章.md",
            SPECS_DIR / "1-reqs/requirements.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "tmp/ideas.md"
        ]
        for f in intro_files:
            if f.exists():
                intro_text += read_text_safe(f) + "\n"
                
    if not intro_text.strip():
        log_warning("未提供项目简介且未找到基线文档，将使用默认 CCC 码。")
        log_info("建议提供 --intro 参数或先创建 specs/govs/G02-项目宪章.md")
        
    return _infer_ccc_from_text(intro_text, prefix)


def _get_all_existing_ids() -> set[str]:
    """获取所有已存在的文档引用编号。"""
    checker = DocumentCodingChecker(SPECS_DIR)
    existing_ids = set()
    for root, _, files in os.walk(SPECS_DIR):
        for file in files:
            ref_id = checker.extract_reference_id(file)
            if ref_id:
                existing_ids.add(ref_id)
    return existing_ids


def create_requirement(args: argparse.Namespace) -> int:
    """创建需求文档并刷新索引。
    
    文件名格式：RQ-<CCC><NN>-<SLUG>需求.md
    示例：RQ-10102-用户注册需求.md
    """
    slug = args.slug
    if not slug:
        log_error("缺少需求简短描述参数")
        return 1
    
    ccc = _resolve_ccc(args, "RQ")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"1-reqs/RQ-{ccc}{nn}-{slug}需求.md"
    return _create_from_template("templates/req.template.md", target)


def create_design(args: argparse.Namespace) -> int:
    """创建设计文档并刷新索引。
    
    文件名格式：DS-<CCC><NN>-<SLUG>设计.md
    示例：DS-20101-API网关认证设计.md
    """
    slug = args.slug
    if not slug:
        log_error("缺少设计简短描述参数")
        return 1
    
    ccc = _resolve_ccc(args, "DS")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"2-designs/DS-{ccc}{nn}-{slug}设计.md"
    return _create_from_template("templates/design.template.md", target)


def create_adr(args: argparse.Namespace) -> int:
    """创建 ADR 文档并刷新索引。
    
    文件名格式：ADR-<CCC><NN>-<SLUG>决策.md
    示例：ADR-10101-引入Redis缓存决策.md
    """
    slug = args.slug
    if not slug:
        log_error("缺少决策简短描述参数")
        return 1
    
    ccc = _resolve_ccc(args, "ADR")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    
    target = f"adrs/ADR-{ccc}{nn}-{slug}决策.md"
    return _create_from_template("templates/adr.template.md", target)


def create_task(args: argparse.Namespace) -> int:
    """创建任务文档并刷新索引。
    
    文件名格式：TK-<CCC><YYWW><NN>-<SLUG>任务.md
    示例：TK-201260901-前端页面开发任务.md
    """
    slug = args.slug
    if not slug:
        log_error("缺少任务简短描述参数")
        return 1
    
    ccc = _resolve_ccc(args, "TK")
    nn = args.nn or get_next_nn(ccc, _get_all_existing_ids())
    yyww = get_yyww()
    
    target = f"3-tasks/TK-{ccc}{yyww}{nn}-{slug}任务.md"
    return _create_from_template("templates/task.template.md", target)


def create_test(args: argparse.Namespace) -> int:
    """创建测试文档并刷新索引。"""
    scope_slug = validating_slug_value(args.scope, "scope")
    if scope_slug is None:
        return 1
    test_id_slug = validating_slug_value(args.test_id, "test_id")
    if test_id_slug is None:
        return 1
    target = f"tests/test-{scope_slug}-{test_id_slug}.md"
    return _create_from_template("templates/test.template.md", target)


def create_release(args: argparse.Namespace) -> int:
    """创建发布文档并刷新索引。"""
    if not validating_semver(args.version):
        return 1
    target = f"releases/release-{get_current_date_slug()}-v{args.version}.md"
    return _create_from_template("templates/release.template.md", target)


def generate_traceability_matrix(_: argparse.Namespace) -> int:
    """生成并更新追溯矩阵（JSON/Markdown）。"""
    json_path, md_path, req_count = generate_traceability_outputs(SPECS_DIR)
    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"已生成：{json_path}")
    log_info(f"已更新：{md_path}")
    log_info(f"追溯矩阵条目：{req_count}")
    return 0


def generate_agent_dispatch(_: argparse.Namespace) -> int:
    """生成 Agent/Skill 统一调度规则。"""
    target, warnings, errors = write_agent_dispatch_file(SPECS_DIR)
    for warning in warnings:
        log_warning(warning)
    for error in errors:
        log_error(error)

    if errors:
        return 1

    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"已生成：{target}")
    return 0


def _reading_agent_dispatch_payload() -> tuple[dict[str, object], list[str], list[str]]:
    """读取或即时构建调度规则载荷。"""
    dispatch_path = SPECS_DIR / "meta/index/agent-dispatch.json"
    if dispatch_path.exists():
        try:
            payload = json.loads(read_text_safe(dispatch_path))
            return payload, [], []
        except json.JSONDecodeError as exc:
            log_warning(f"调度规则 JSON 解析失败，回退为即时构建：{exc}")
    return build_agent_dispatch_payload(SPECS_DIR)


def resolve_agent_dispatch_command(args: argparse.Namespace) -> int:
    """根据 Agent/Skill 定义解析任务调度建议。"""
    payload, warnings, errors = _reading_agent_dispatch_payload()
    for warning in warnings:
        log_warning(warning)
    for error in errors:
        log_error(error)

    if errors:
        return 1

    result = resolve_agent_dispatch(
        payload=payload,
        task=args.task,
        stage=args.stage,
        requested_skills=args.skills,
    )

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    log_info(f"主责 Agent：{result['primary_agent']}")
    log_info(f"建议 Skill：{', '.join(result['recommended_skills']) or '(无)'}")
    log_info(f"协同 Agent：{', '.join(result['support_agents']) or '(无)'}")
    for reason in result["primary_reasons"]:
        log_info(f"调度依据：{reason}")
    for rule in result["shared_skill_arbitration"]:
        log_info(f"共享 Skill 仲裁：{rule.get('skill')} -> {rule.get('rule')}")
    return 0


def _parsing_extra_entries(raw_items: list[str] | None) -> list[tuple[str, str]]:
    """解析 `--extra-entry path:format` 参数列表。"""
    parsed: list[tuple[str, str]] = []
    for raw in raw_items or []:
        if ":" not in raw:
            raise ValueError(f"extra-entry 格式错误（需 path:format）：{raw}")
        path, fmt = raw.split(":", 1)
        path = path.strip()
        fmt = fmt.strip()
        if not path or not fmt:
            raise ValueError(f"extra-entry 格式错误（空字段）：{raw}")
        parsed.append((path, fmt))
    return parsed


def generate_tool_adapters(_: argparse.Namespace) -> int:
    """生成/同步多工具入口工件。"""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    manifest_path = write_tool_adapter_manifest(REPO_ROOT, manifest)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)
    log_info(f"已写入适配清单：{manifest_path}")
    log_info(f"已同步入口工件：{', '.join(written_entries) or '(无)'}")
    log_info(f"清单路径：{MANIFEST_REL_PATH}")
    return 0


def list_tool_adapters_command(_: argparse.Namespace) -> int:
    """列出多工具适配清单。"""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    rows = list_tool_adapters(manifest)
    if not rows:
        log_warning("未配置任何工具适配项")
        return 0

    log_info("工具适配清单：")
    for row in rows:
        log_info(
            " | ".join(
                [
                    f"tool={row['tool_id']}",
                    f"name={row['display_name']}",
                    f"enabled={row['enabled']}",
                    f"format={row['definition_format']}",
                    f"entries={row['entries']}",
                ]
            )
        )
    return 0


def add_tool_adapter_command(args: argparse.Namespace) -> int:
    """向多工具适配清单新增工具。"""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    try:
        extra_entries = _parsing_extra_entries(args.extra_entry)
        manifest = add_tool_adapter(
            manifest=manifest,
            tool_id=args.tool_id,
            display_name=args.display_name,
            entry_file=args.entry_file,
            entry_format=args.entry_format,
            shared_entry=args.shared_entry,
            extra_entries=extra_entries,
        )
    except ValueError as exc:
        log_error(str(exc))
        return 1

    write_tool_adapter_manifest(REPO_ROOT, manifest)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)
    log_info(f"已新增工具适配：{args.tool_id}")
    log_info(f"已同步入口工件：{', '.join(written_entries) or '(无)'}")
    return 0


def remove_tool_adapter_command(args: argparse.Namespace) -> int:
    """从多工具适配清单移除工具。"""
    manifest = load_tool_adapter_manifest(REPO_ROOT)
    try:
        manifest, removable_paths = remove_tool_adapter(manifest, args.tool_id)
    except ValueError as exc:
        log_error(str(exc))
        return 1

    write_tool_adapter_manifest(REPO_ROOT, manifest)
    deleted_paths = delete_entry_files(REPO_ROOT, removable_paths)
    written_entries = sync_tool_adapter_entries(REPO_ROOT, manifest)

    log_info(f"已移除工具适配：{args.tool_id}")
    log_info(f"已回收入口工件：{', '.join(deleted_paths) or '(无)'}")
    log_info(f"当前入口工件：{', '.join(written_entries) or '(无)'}")
    return 0


def check_spec_status(_: argparse.Namespace) -> int:
    """检查规范必需文件是否齐全。"""
    file_code = check_required_files(SPECS_DIR, REQUIRED_SPEC_FILES)
    if file_code != 0:
        return file_code

    issues: list[str] = []
    for rel, section, labels in [
        ("1-reqs/requirements.md", "元信息", ("文档编号", "版本", "负责人", "日期")),
        ("2-designs/architecture.md", "元信息", ("文档编号", "版本", "负责人", "日期")),
        ("3-tasks/task-plan.md", "任务清单", ("任务编号", "描述", "负责人", "验收标准", "状态")),
        ("tests/test-plan.md", "元信息", ("文档编号", "版本", "负责人", "日期")),
        ("releases/release-plan.md", "元信息", ("版本", "负责人", "日期")),
        ("changelogs/CHANGELOG.md", "版本信息", ("版本", "日期", "发布负责人")),
        ("runbook/runbook.md", "元信息", ("文档编号", "版本", "负责人", "日期")),
    ]:
        path = SPECS_DIR / rel
        for issue in check_required_nonempty_bullets(path, section, labels):
            issues.append(f"{path} -> {issue}")

    if issues:
        log_error("主工件存在占位或缺失内容：")
        for issue in issues:
            log_error(f"- {issue}")
        return 1
    log_info("完整性检查通过")
    return 0


def check_requirement_doc(_: argparse.Namespace) -> int:
    """校验主需求文档内容结构。"""
    return check_requirement_file(SPECS_DIR / "1-reqs/requirements.md")


def check_design_doc(_: argparse.Namespace) -> int:
    """校验主架构设计文档内容结构。"""
    return check_design_file(SPECS_DIR / "2-designs/architecture.md")


def check_changelog(_: argparse.Namespace) -> int:
    """检查变更日志文件是否存在且非空。"""
    return check_changelog_file(SPECS_DIR / "changelogs/CHANGELOG.md")


def build_governance_token_requirements() -> dict[str, list[str]]:
    """构建治理检查的必需字段与关键文本规则。"""
    return {
        "govs/G04-角色职责.md": [
            "重大变更与发布：Owner 与评审 Agent 联签。",
            "发布前验证：测试 Agent 负责验证事实输出，不负责最终放行审批。",
            "发布执行：发布 Agent 负责执行与归档，不负责最终放行审批。",
        ],
        "govs/G05-Agent协作宪章.md": [
            "发布放行由 Owner 与评审角色联签，测试角色仅提供验证事实，发布角色仅执行发布。",
        ],
        "govs/G03-质量门禁.md": [
            "发布审批状态已满足（Owner + reviewer-agent 联签）。",
            "### 角色责任",
            "tester-agent：提供验证结果与风险分级。",
            "reviewer-agent：给出阻断/放行建议并参与联签。",
            "release-agent：执行已批准发布并归档。",
            "## 一页式 RACI（REL-Gate）",
        ],
        "releases/release-plan.md": [
            "## 审批记录",
            "- Owner 审批：",
            "- reviewer-agent 审批：",
            "- 联签结论：",
            "- 审批时间：",
        ],
        "templates/release.template.md": [
            "## 审批记录",
            "- Owner 审批：",
            "- reviewer-agent 审批：",
            "- 联签结论：",
            "- 审批时间：",
        ],
        "meta/index/capability-matrix.md": [
            "## 元信息",
            "| 能力 | 文档 | 优先级 | 成熟度 | Owner | 依赖 | 状态 |",
            "| Agent | 主责能力 | 优先级 | 成熟度 | 依赖 Skill | 状态 |",
            "| Skill | 主责 Agent | 优先级 | 成熟度 | 依赖 | 状态 |",
        ],
    }


def check_governance_token_files(required_tokens_by_file: dict[str, list[str]]) -> list[str]:
    """检查治理关键文件中必需 token 是否完整。"""
    issues: list[str] = []
    for rel, tokens in required_tokens_by_file.items():
        path = SPECS_DIR / rel
        code = check_path_exists(path, "缺少治理文件：{path}", "治理文件为空：{path}")
        if code != 0:
            issues.append(f"missing:{path}")
            continue

        text = read_text_safe(path)
        for token in tokens:
            if token not in text:
                issues.append(f"治理字段缺失：{path} -> {token}")
    return issues


def check_governance_release_records(required_release_labels: set[str]) -> list[str]:
    """检查发布记录中的审批字段是否齐全。"""
    issues: list[str] = []
    for path in sorted((SPECS_DIR / "releases").glob("release-*.md")):
        issues.extend(check_structured_bullets(path, "审批记录", required_release_labels, "发布审批"))
    return issues


def check_governance_metadata_sections(required_metadata_labels: set[str]) -> list[str]:
    """检查治理与角色文档元信息字段是否齐全。"""
    issues: list[str] = []
    metadata_targets: list[Path] = []
    metadata_targets.extend(sorted((SPECS_DIR / "govs").glob("*.md")))
    metadata_targets.extend(sorted((SPECS_DIR / "agents").glob("*.md")))
    metadata_targets.extend(sorted((SPECS_DIR / "skills").glob("*.md")))
    for path in metadata_targets:
        issues.extend(check_structured_bullets(path, "元信息", required_metadata_labels, "元信息"))
    return issues


def check_governance(_: argparse.Namespace) -> int:
    """执行治理审批链完整性检查。"""
    required_tokens_by_file = build_governance_token_requirements()
    required_release_labels = {
        normalize_md_token("Owner 审批"),
        normalize_md_token("reviewer-agent 审批"),
        normalize_md_token("联签结论"),
        normalize_md_token("审批时间"),
    }
    required_metadata_labels = {
        normalize_md_token("版本"),
        normalize_md_token("生效日期"),
        normalize_md_token("最后更新"),
        normalize_md_token("变更说明"),
    }

    issues: list[str] = []
    issues.extend(check_governance_token_files(required_tokens_by_file))
    issues.extend(check_governance_release_records(required_release_labels))
    issues.extend(check_governance_metadata_sections(required_metadata_labels))

    failed = False
    for issue in issues:
        if issue.startswith("missing:"):
            failed = True
            continue
        log_error(issue)
        failed = True

    if failed:
        return 1

    log_info("治理审批链检查通过")
    return 0


def check_spec_drift(_: argparse.Namespace) -> int:
    """检查代码与规范来源标记的一致性。"""
    return check_drift_files(REPO_ROOT, SUPPORTED_CODE_SUFFIXES, SPEC_MARK)


def check_project_dependencies(_: argparse.Namespace) -> int:
    """执行依赖风险与可复现性检查。"""
    return check_dependencies(REPO_ROOT)


def check_project_code_quality(_: argparse.Namespace) -> int:
    """执行轻量代码质量检查。"""
    return check_code_quality(REPO_ROOT)


def check_spec_completeness(_: argparse.Namespace) -> int:
    """刷新追溯矩阵后检查需求链路完整性。"""
    generate_traceability_outputs(SPECS_DIR)
    return check_completeness(SPECS_DIR)


def check_doc_naming(_: argparse.Namespace) -> int:
    """检查 specs 文档命名规范与索引登记完整性。"""
    index_file = SPECS_DIR / "meta/index/index.md"
    index_text = read_text_safe(index_file) if index_file.exists() else ""
    index_registered_files = extract_registered_ids(index_text)
    has_structured_file_section = "## 文件" in index_text

    failed = False
    for file in sorted(SPECS_DIR.rglob("*")):
        if not file.is_file():
            continue
        if "__pycache__" in file.parts:
            continue

        rel = file.relative_to(SPECS_DIR).as_posix()
        if file.name in ("README.md", "INDEX.md") or is_ccc_coded(file.name): continue
        checker = NamingChecker(BANNED_NAMES, SPECIAL_MARKDOWN_NAMES)
        issues = checker.validate_path(file, rel)
        if issues:
            failed = True
            for issue in issues:
                log_error(issue)
            if any("不支持的工具文件类型" in issue or "不支持的文件类型" in issue for issue in issues):
                continue

        if rel != "meta/index/index.md" and index_text:
            if has_structured_file_section:
                if rel not in index_registered_files:
                    log_error(f"未在索引登记：{file}")
                    failed = True
            elif f"`{rel}`" not in index_text:
                log_error(f"未在索引登记：{file}")
                failed = True

    if failed:
        return 1

    log_info("命名检查通过")
    return 0


def check_document_coding(_: argparse.Namespace) -> int:
    """检查文档编码规范（CCC-NN-YYWW体系）。"""
    checker = _getting_document_coding_checker()
    passed, errors, warnings = checker.check_all()
    
    if errors:
        log_error(f"发现 {len(errors)} 个编码错误：")
        for error in errors:
            log_error(f"  - {error}")
    
    if warnings:
        log_warning(f"发现 {len(warnings)} 个警告：")
        for warning in warnings:
            log_warning(f"  - {warning}")
    
    if passed and not errors:
        log_info("文档编码规范检查通过")
        return 0
    
    return 1 if errors else 0


def locate_document(args: argparse.Namespace) -> int:
    """根据文档编号定位文档。"""
    checker = _getting_document_coding_checker()
    ref_id = args.ref_id
    
    # 校验引用编号格式
    # 对于 RQ-10102 格式，提取 RQ
    # 对于 G01 格式，提取 G（字母部分）
    if '-' in ref_id:
        prefix = ref_id.split('-')[0]
    else:
        # G01, S01 等格式，提取首字母
        prefix = ref_id[0] if ref_id else ""
    
    valid_prefixes = ['RQ', 'DS', 'TK', 'ADR', 'G', 'S']
    if prefix not in valid_prefixes:
        log_error(f"无效的文档编号格式: {ref_id}")
        log_error(f"支持的类型: {', '.join(valid_prefixes)}")
        return 1
    
    path, error, matches = checker.locate_document(ref_id)
    
    if error:
        log_error(error)
        return 1
    
    if not path:
        log_error(f"未找到文档编号: {ref_id}")
        return 1
    
    # 输出相对路径
    rel_path = path.relative_to(REPO_ROOT)
    print(str(rel_path))
    return 0


def read_document(args: argparse.Namespace) -> int:
    """根据文档编号读取文档内容。"""
    ref_id = args.ref_id
    
    path, error, matches = resolve_spec_path(ref_id)
    
    if error:
        log_error(error)
        return 1
    
    if not path:
        log_error(f"未找到文档编号: {ref_id}")
        return 1
    
    # 读取并输出文档内容
    try:
        content = read_text_safe(path)
        print(content)
        return 0
    except Exception as exc:
        log_error(f"读取文档失败: {exc}")
        return 1


def trace_document_dependencies(args: argparse.Namespace) -> int:
    """追踪文档依赖关系（关联的需求、设计、任务、代码）。"""
    ref_id = args.ref_id
    
    # 执行依赖追踪
    result = trace_dependencies(SPECS_DIR, ref_id, REPO_ROOT)
    
    if result.errors:
        for error in result.errors:
            log_error(error)
        return 1
    
    # 输出格式选择
    if hasattr(args, 'as_json') and args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    
    # 输出可读格式
    _print_dependency_trace(result)
    return 0


def _print_dependency_trace(result) -> None:
    """打印依赖追踪结果（可读格式）。"""
    print(f"\n{'='*70}")
    print(f"文档依赖追踪: {result.ref_id}")
    print(f"{'='*70}")
    
    # 源文档信息
    if result.source_doc:
        print("\n📄 源文档:")
        print(f"   ID: {result.source_doc.doc_id}")
        print(f"   标题: {result.source_doc.doc_title}")
        print(f"   路径: {result.source_doc.doc_path}")
        print(f"   类型: {result.source_doc.doc_type}")
    
    # 关联需求
    if result.related_reqs:
        print(f"\n📋 关联需求 ({len(result.related_reqs)}):")
        for doc in result.related_reqs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     路径: {doc.doc_path}")
            if doc.context:
                print(f"     上下文: {doc.context}")
    
    # 关联设计
    if result.related_designs:
        print(f"\n🎨 关联设计 ({len(result.related_designs)}):")
        for doc in result.related_designs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     路径: {doc.doc_path}")
            if doc.context:
                print(f"     上下文: {doc.context}")
    
    # 关联任务
    if result.related_tasks:
        print(f"\n📌 关联任务 ({len(result.related_tasks)}):")
        for doc in result.related_tasks:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     路径: {doc.doc_path}")
            if doc.context:
                print(f"     上下文: {doc.context}")
    
    # 关联测试
    if result.related_tests:
        print(f"\n🧪 关联测试 ({len(result.related_tests)}):")
        for doc in result.related_tests:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     路径: {doc.doc_path}")
            if doc.context:
                print(f"     上下文: {doc.context}")
    
    # 关联ADR
    if result.related_adrs:
        print(f"\n🏛️ 关联架构决策 ({len(result.related_adrs)}):")
        for doc in result.related_adrs:
            print(f"   • {doc.doc_id}: {doc.doc_title}")
            print(f"     路径: {doc.doc_path}")
            if doc.context:
                print(f"     上下文: {doc.context}")
    
    # 代码引用
    if result.code_refs:
        print(f"\n💻 代码实现 ({len(result.code_refs)}):")
        for ref in result.code_refs:
            print(f"   • {ref.file_path}:{ref.line_number}")
            if ref.module_name:
                print(f"     模块: {ref.module_name}")
            if ref.function_name:
                print(f"     函数/类: {ref.function_name}")
            print(f"     上下文: {ref.context}")
    elif result.source_doc and result.source_doc.doc_type == "requirement":
        print("\n⚠️ 未找到代码实现引用")
        print(f"   提示: 确保代码中包含 '{result.ref_id}' 或 '{SPEC_MARK}' 标记")
    
    print(f"\n{'='*70}\n")


def rename_document(args: argparse.Namespace) -> int:
    """更换文档编号。
    
    支持两种使用方式:
    1. 传入完整文件名: rename-document "旧文件名.md" "新文件名.md"
    2. 传入文档编号: rename-document --by-ref-id "RQ-10102" "新文件名.md"
    """
    checker = _getting_document_coding_checker()
    
    # 判断是使用文档编号还是完整文件名
    if hasattr(args, 'by_ref_id') and args.by_ref_id:
        # 通过文档编号定位文件
        path, error, matches = resolve_spec_path(args.old_identifier)
        
        if error:
            log_error(error)
            return 1
        
        if not path:
            log_error(f"未找到文档编号: {args.old_identifier}")
            return 1
        
        old_filename = path.name
    else:
        # 直接使用完整文件名
        old_filename = args.old_identifier
    
    success, message = checker.rename_document(old_filename, args.new_filename)
    
    if success:
        log_info(message)
        # 重命名后刷新索引
        index_code = refresh_index_after_change()
        if index_code != 0:
            return index_code
        return 0
    else:
        log_error(message)
        return 1


def collect_governance_capabilities() -> list[tuple[str, str, str]]:
    """收集治理能力矩阵行数据。"""
    rows: list[tuple[str, str, str]] = []
    for capability_id, rel in [
        ("G01", "govs/G01-治理与流程.md"),
        ("G02", "govs/G02-项目宪章.md"),
        ("G03", "govs/G03-质量门禁.md"),
        ("G04", "govs/G04-角色职责.md"),
        ("G05", "govs/G05-Agent协作宪章.md"),
    ]:
        path = SPECS_DIR / rel
        if not path.exists():
            continue
        title = read_first_heading(path) or path.stem
        rows.append((capability_id, rel, title))
    return rows


def collect_agent_capabilities() -> list[tuple[str, str, str]]:
    """收集 Agent 能力矩阵行数据。"""
    return _collect_capabilities_from_glob("agents", "*-agent.md", "AGENT")


def collect_skill_capabilities() -> list[tuple[str, str, str]]:
    """收集 Skill 能力矩阵行数据。"""
    return _collect_capabilities_from_glob("skills", "*-skill.md", "SKILL")


def _collect_capabilities_from_glob(
    directory: str,
    pattern: str,
    capability_prefix: str,
) -> list[tuple[str, str, str]]:
    """按目录与匹配模式收集能力矩阵行。"""
    rows: list[tuple[str, str, str]] = []
    files = sorted((SPECS_DIR / directory).glob(pattern))
    for idx, path in enumerate(files, start=1):
        rel = path.relative_to(SPECS_DIR).as_posix()
        title = read_first_heading(path) or path.stem
        rows.append((f"{capability_prefix}-{idx:03d}", rel, title))
    return rows


def generate_index(_: argparse.Namespace) -> int:
    """生成并写入 specs 全量索引文档。"""
    index = SPECS_DIR / "meta/index/index.md"
    markdown_counts = count_specs_by_dir(SPECS_DIR)

    lines: list[str] = ["# specs 总索引", "", "## 文档总览表"]
    lines.extend(
        [
            "| 类别 | 目录 | 文件数 | 核心能力 | 状态 |",
            "|---|---|---:|---|---|",
        ]
    )

    for category, directory in CATEGORY_DIRECTORY_ROWS:
        count = markdown_counts.get(directory, 0)
        capability = "✅" if count > 0 else "⚪"
        status = "完整" if count > 0 else "待补"
        lines.append(f"| {category} | `{directory}/` | {count} | {capability} | {status} |")

    lines.extend(["", "## 核心能力清单", ""])
    lines.extend(["### 治理能力", "| ID | 文档 | 说明 | 状态 |", "|---|---|---|---|"])
    governance_rows = collect_governance_capabilities()
    if governance_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in governance_rows)
    else:
        lines.append("| - | - | 暂无 | ⚪ |")

    lines.extend(["", "### Agent 能力", "| ID | 文档 | 说明 | 状态 |", "|---|---|---|---|"])
    agent_rows = collect_agent_capabilities()
    if agent_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in agent_rows)
    else:
        lines.append("| - | - | 暂无 | ⚪ |")

    lines.extend(["", "### Skill 能力", "| ID | 文档 | 说明 | 状态 |", "|---|---|---|---|"])
    skill_rows = collect_skill_capabilities()
    if skill_rows:
        lines.extend(f"| {cap_id} | `{doc}` | {desc} | ✅ |" for cap_id, doc, desc in skill_rows)
    else:
        lines.append("| - | - | 暂无 | ⚪ |")

    lines.extend(["", "## 目录"])
    lines.extend(f"- {name}" for name in list_top_directories())
    lines.extend(["", "## 文件"])
    lines.extend(f"- `{rel}`" for rel in list_files_depth_two(SPECS_DIR))
    return write_index(index, lines)


def initialize_project(_: argparse.Namespace) -> int:
    """初始化 specs 目录、模板与基线文档。"""
    for directory in DIRECTORIES:
        (SPECS_DIR / directory).mkdir(parents=True, exist_ok=True)

    for rel, content in TEMPLATE_CONTENTS.items():
        write_file_safe(SPECS_DIR / rel, content)

    for rel, content in SEED_CONTENTS.items():
        write_file_safe(SPECS_DIR / rel, content)

    ensure_gov_metadata()
    index_code = refresh_index_after_change()
    if index_code != 0:
        return index_code
    log_info(f"specs 初始化完成：{SPECS_DIR}")
    return 0


def build_default_handlers() -> dict[str, CommandHandler]:
    """构建默认命令处理函数映射。"""
    return build_handler_map(
        {
            "initialize": initialize_project,
            "version": show_version,
            "generate-index": generate_index,
            "generate-traceability-matrix": generate_traceability_matrix,
            "generate-agent-dispatch": generate_agent_dispatch,
            "generate-tool-adapters": generate_tool_adapters,
            "create-requirement": create_requirement,
            "create-design": create_design,
            "create-adr": create_adr,
            "create-task": create_task,
            "create-test": create_test,
            "create-release": create_release,
            "check-status": check_spec_status,
            "check-quality-gates": check_quality_gates,
            "validate-requirement": check_requirement_doc,
            "validate-design": check_design_doc,
            "check-changelog": check_changelog,
            "check-governance": check_governance,
            "check-dependencies": check_project_dependencies,
            "check-code-quality": check_project_code_quality,
            "check-completeness": check_spec_completeness,
            "check-naming": check_doc_naming,
            "check-document-coding": check_document_coding,
            "bundle-task-context": bundle_task_context,
            "trace-code": trace_code_origins,
            "locate-document": locate_document,
            "read-document": read_document,
            "trace-dependencies": trace_document_dependencies,
            "rename-document": rename_document,
            "build-reference-index": build_reference_index,
            "find-references-to": find_references_to,
            "find-references-from": find_references_from,
            "update-references": update_references,
            "delete-references": delete_references,
            "check-orphaned-references": check_orphaned_references,
            "reference-report": generate_reference_report,
            "check-drift": check_spec_drift,
            "resolve-agent-dispatch": resolve_agent_dispatch_command,
            "list-tool-adapters": list_tool_adapters_command,
            "add-tool-adapter": add_tool_adapter_command,
            "remove-tool-adapter": remove_tool_adapter_command,
        }
    )


__all__ = [
    "add_tool_adapter_command",
    "build_default_handlers",
    "check_changelog",
    "check_design_doc",
    "check_doc_naming",
    "check_document_coding",
    "check_governance",
    "check_project_code_quality",
    "check_project_dependencies",
    "check_requirement_doc",
    "check_spec_completeness",
    "check_spec_drift",
    "check_spec_status",
    "bundle_task_context",
    "show_version",
    "trace_code_origins",
    "locate_document",
    "read_document",
    "trace_document_dependencies",
    "rename_document",
    "create_adr",
    "create_design",
    "create_release",
    "create_requirement",
    "create_task",
    "create_test",
    "generate_index",
    "generate_agent_dispatch",
    "generate_tool_adapters",
    "generate_traceability_matrix",
    "initialize_project",
    "list_tool_adapters_command",
    "remove_tool_adapter_command",
    "resolve_agent_dispatch_command",
    "build_reference_index",
    "find_references_to",
    "find_references_from",
    "update_references",
    "delete_references",
    "check_orphaned_references",
    "generate_reference_report",
]


def build_reference_index(args: argparse.Namespace) -> int:
    """构建文档引用关系索引。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    manager.scan_all_references()
    manager.save_index()
    
    index = manager.build_reference_index()
    stats = index.get('stats', {})
    
    log_info("引用索引构建完成:")
    log_info(f"  - 总引用数: {stats.get('total_references', 0)}")
    log_info(f"  - 引用源文件数: {stats.get('total_source_files', 0)}")
    log_info(f"  - 被引用目标文件数: {stats.get('total_target_files', 0)}")
    log_info(f"  - 索引文件: {manager.index_path.relative_to(REPO_ROOT)}")
    
    return 0


def find_references_to(args: argparse.Namespace) -> int:
    """查询哪些文档引用了指定编号。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    refs = manager.find_references_to(args.ref_id)
    
    if not refs:
        print(f"没有找到引用 {args.ref_id} 的文档")
        return 0
    
    print(f"\n引用了 {args.ref_id} 的文档（共 {len(refs)} 处）:\n")
    
    # 按源文件分组
    by_source: dict = {}
    for ref in refs:
        source = ref['source_file']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(ref)
    
    for source, items in sorted(by_source.items()):
        print(f"📄 {source}")
        for item in items:
            print(f"   第 {item['line_number']} 行: {item['context'][:80]}...")
        print()
    
    return 0


def find_references_from(args: argparse.Namespace) -> int:
    """查询指定文档引用了哪些文档。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    refs = manager.find_references_from(args.ref_id)
    
    if not refs:
        print(f"{args.ref_id} 没有引用其他文档")
        return 0
    
    print(f"\n{args.ref_id} 引用的文档（共 {len(refs)} 处）:\n")
    
    # 按类型分组
    by_type: dict = {}
    for ref in refs:
        ref_type = ref.get('ref_type', 'doc')
        if ref_type not in by_type:
            by_type[ref_type] = []
        by_type[ref_type].append(ref)
    
    for ref_type, items in sorted(by_type.items()):
        type_name = {'doc': '📄 文档引用', 'index': '📑 索引引用', 'code': '💻 代码引用'}.get(ref_type, ref_type)
        print(f"{type_name}:")
        for item in items:
            print(f"   - {item['target_ref_id']} ({item['target_file']})")
        print()
    
    return 0


def update_references(args: argparse.Namespace) -> int:
    """批量更新引用关系。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    
    count, log = manager.update_references(
        args.old_ref_id, 
        args.new_ref_id, 
        dry_run=args.dry_run
    )
    
    for line in log:
        if args.dry_run:
            print(line)
        else:
            if line.startswith("错误"):
                log_error(line)
            else:
                log_info(line)
    
    if not args.dry_run and count > 0:
        log_info(f"共更新 {count} 处引用")
    
    return 0 if not any(line.startswith("错误") for line in log) else 1


def delete_references(args: argparse.Namespace) -> int:
    """删除对指定文档的引用。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    
    count, log = manager.delete_references_to(args.ref_id, dry_run=args.dry_run)
    
    for line in log:
        if args.dry_run:
            print(line)
        else:
            if line.startswith("错误"):
                log_error(line)
            else:
                log_info(line)
    
    return 0


def check_orphaned_references(args: argparse.Namespace) -> int:
    """检查孤立的引用。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    orphaned = manager.check_orphaned_references()
    
    if not orphaned:
        log_info("没有发现孤立的引用")
        return 0
    
    log_warning(f"发现 {len(orphaned)} 个孤立引用:")
    for item in orphaned:
        print(f"  - {item['source_file']}:{item['line_number']}")
        print(f"    引用目标: {item['target_file']}")
        print(f"    建议: {item['suggestion']}")
    
    return 0


def generate_reference_report(args: argparse.Namespace) -> int:
    """生成文档引用关系报告。"""
    from sdd.checkers.referencechecker import ReferenceManager
    
    manager = ReferenceManager(str(SPECS_DIR))
    report = manager.generate_reference_report()
    
    print(report)
    
    # 保存报告
    report_path = SPECS_DIR / "meta/index" / "reference-report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    log_info(f"\n报告已保存到: {report_path.relative_to(REPO_ROOT)}")
    
    return 0


def bundle_task_context(args: argparse.Namespace) -> int:
    """聚合任务相关的上下文（需求、设计、ADR）到 tmp 目录。"""
    task_id = args.task_id.upper()
    if not task_id.startswith("TK-"):
        log_error(f"无效的任务 ID: {task_id} (需以 TK- 开头)")
        return 1

    # 1. 定位任务文档
    task_path, error_msg, _ = resolve_spec_path(task_id)
    if error_msg:
        log_error(error_msg)
        return 1
    if not task_path:
        log_error(f"未找到任务文档: {task_id}")
        return 1

    log_info(f"正在聚合任务上下文: {task_id} <- {task_path.name}")

    # 2. 解析任务文档中的关联引用
    content = read_text_safe(task_path)
    # 匹配 RQ-10101, DS-20101, ADR-10101, TEST-10101 等
    ref_pattern = re.compile(r"\b([A-Z]{1,4}-[A-Z0-9-]+)\b")
    found_refs = ref_pattern.findall(content)
    
    # 过滤重复并排除自己
    unique_refs = []
    seen = {task_id}
    for ref in found_refs:
        # 特殊处理 DS- 前缀，因为 resolve_spec_path 期望的是 DS- 或 DS-XXX
        # 我们的规范中 DSN 可能会简写为 DS
        search_ref = ref
        if ref.startswith("DS-"):
            search_ref = ref.replace("DS-", "DS-")
            
        if search_ref not in seen:
            unique_refs.append(search_ref)
            seen.add(search_ref)

    # 3. 聚合内容
    output_lines = [
        f"# 任务上下文聚合: {task_id}",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 原始任务文件: {task_path.name}",
        "",
        "> [!IMPORTANT]",
        "> 本文件由 SDD 工具自动生成，仅作为开发上下文参考。**请勿直接修改本文件**，所有变更应在 `specs/` 下对应的源文档中进行。",
        "",
        "---",
        "## [TASK] 任务定义 (Task Definition)",
        content,
        "",
    ]

    for ref in unique_refs:
        doc_path, _, _ = resolve_spec_path(ref)
        if doc_path and doc_path.exists():
            log_info(f"  + 聚合关联文档: {ref}")
            doc_content = read_text_safe(doc_path)
            
            # 确定文档类型
            doc_type = "DOC"
            if ref.startswith("RQ"):
                doc_type = "REQUIREMENT"
            elif ref.startswith("DS"):
                doc_type = "DESIGN"
            elif ref.startswith("ADR"):
                doc_type = "ADR"
            elif ref.startswith("TEST"):
                doc_type = "TEST"

            output_lines.extend([
                "---",
                f"## [{doc_type}] {ref} ({doc_path.name})",
                doc_content,
                "",
            ])
        else:
            log_warning(f"  ! 跳过未找到的关联文档: {ref}")

    # 4. 写入 tmp 目录
    tmp_dir = REPO_ROOT / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    output_file = tmp_dir / f"TASK-CONTEXT-{task_id}.md"
    
    try:
        output_file.write_text("\n".join(output_lines), encoding="utf-8")
        log_info(f"上下文聚合完成: {output_file.relative_to(REPO_ROOT)}")
        print(f"\n[SUCCESS] Context bundled at: {output_file.relative_to(REPO_ROOT)}\n")
        return 0
    except Exception as e:
        log_error(f"写入聚合文件失败: {e}")
        return 1


def check_quality_gates(args: argparse.Namespace) -> int:
    """执行综合质量门禁检查。聚合命名、漂移与完备性检查。"""
    log_info(">>> 正在执行 SDD 质量门禁校验...")
    
    # 1. 刷新索引与追溯矩阵（基础）
    if generate_index(args) != 0:
        return 1
    if generate_traceability_matrix(args) != 0:
        return 1

    # 2. 执行核心校验
    failed = False
    
    log_info("\n[1/3] 检查命名规范与索引登记...")
    if check_doc_naming(args) != 0:
        failed = True

    log_info("\n[2/3] 检查规范漂移与引用有效性...")
    if check_spec_drift(args) != 0:
        failed = True

    log_info("\n[3/3] 检查全链路完备性 (REQ -> DSN -> TK -> CODE)...")
    if check_spec_completeness(args) != 0:
        failed = True

    print("\n" + "="*60)
    if failed:
        log_error("质量门禁校验未通过！请修正上述问题后再继续。")
    print("\n" + "="*60)
    if failed:
        log_error("质量门禁校验未通过！请修正上述问题后再继续。")
        print("="*60 + "\n")
        return 1
    else:
        log_info("恭喜！所有质量门禁校验均已通过。")
        print("="*60 + "\n")
        return 0


def show_version(_: argparse.Namespace) -> int:
    """显示 SDD 工具链与治理体系的当前版本。"""
    from sdd.config import SDD_TOOL_VERSION

    # 1. 提取治理版本 (G01)
    gov_version = "未知"
    gov_path = SPECS_DIR / "govs/G01-治理与流程.md"
    if gov_path.exists():
        content = read_text_safe(gov_path)
        match = re.search(r"- 版本：\s*(v[0-9.]+)", content)
        if match:
            gov_version = match.group(1)

    # 2. 提取标准版本 (S01)
    std_version = "未知"
    std_path = SPECS_DIR / "standards/S01-文档编码规范.md"
    if std_path.exists():
        content = read_text_safe(std_path)
        match = re.search(r"- 版本：\s*(v[0-9.]+)", content)
        if match:
            std_version = match.group(1)

    print(f"\n{'='*40}")
    print(" SDD 体系版本报告")
    print(f"{'='*40}")
    print(f"  > 工具链版本 (Tooling):  {SDD_TOOL_VERSION}")
    print(f"  > 治理政策 (Policy):     {gov_version}")
    print(f"  > 文档规范 (Standard):   {std_version}")
    print(f"{'='*40}\n")
    
    return 0


def trace_code_origins(args: argparse.Namespace) -> int:
    """从代码文件的标注中反向追溯原始的需求、设计和任务。"""
    code_path = Path(args.file_path).resolve()
    if not code_path.exists():
        log_error(f"代码文件不存在: {code_path}")
        return 1

    try:
        rel_to_root = code_path.relative_to(REPO_ROOT)
    except ValueError:
        rel_to_root = code_path

    log_info(f"正在从代码追溯规范来源: {rel_to_root}")
    
    content = read_text_safe(code_path)
    # 匹配规范 ID 格式
    ref_pattern = re.compile(r"\b([A-Z]{1,4}-[A-Z0-9-]+)\b")
    found_ids = ref_pattern.findall(content)
    
    if not found_ids:
        log_warning("该文件中未发现规范引用标识（如 RQ-xxx, DS-xxx）")
        return 0

    unique_ids = sorted(list(set(found_ids)))
    
    print(f"\n{'='*60}")
    print(f" 代码追溯报告: {code_path.name}")
    print(f"{'='*60}\n")

    for ref_id in unique_ids:
        # 特殊处理 DS -> DSN
        search_id = ref_id
        if ref_id.startswith("DS-"):
            search_id = ref_id.replace("DS-", "DS-")
            
        doc_path, _, _ = resolve_spec_path(search_id)
        if doc_path and doc_path.exists():
            title = read_first_heading(doc_path)
            rel_path = doc_path.relative_to(SPECS_DIR)
            print(f"  [{ref_id}] -> {title}")
            print(f"    位置: specs/{rel_path}")
            
            # 尝试提取元信息中的负责人或版本
            doc_text = read_text_safe(doc_path)
            meta_lines = doc_text.split("## 元信息", 1)[-1].split("##", 1)[0].splitlines()
            for line in meta_lines:
                if "负责人" in line or "版本" in line or "状态" in line:
                    print(f"    {line.strip().lstrip('-').strip()}")
            print("-" * 40)
        else:
            # 忽略那些看起来像 ID 但不是规范 ID 的词
            pass

    print("\n[INFO] 追溯完成。若需查看详情，请运行: sddtool.py read-document <ID>")
    return 0
