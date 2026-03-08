"""SDD CLI 配置常量与初始化模板内容。"""

from __future__ import annotations

import re
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
SPECS_DIR = TOOLS_DIR.parents[1]  # tools -> meta -> specs
REPO_ROOT = SPECS_DIR.parent

BANNED_NAMES = {"new.md", "final.md", "temp.md"}
SPECIAL_MARKDOWN_NAMES = {"CHANGELOG.md", "README.md"}
SUPPORTED_CODE_SUFFIXES = {".ts", ".js", ".go", ".py", ".rs"}
SPEC_MARK = "Spec:"
# SDD 工具链语义化版本
SDD_TOOL_VERSION = "1.2.0"
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
DATE_COMPACT_FORMAT = "%Y%m%d"
DATE_ISO_FORMAT = "%Y-%m-%d"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

REQUIRED_SPEC_FILES = [
    "govs/G01-治理与流程.md",
    "govs/G02-项目宪章.md",
    "govs/G03-质量门禁.md",
    "govs/G05-Agent协作宪章.md",
    "govs/knowledge-sources.yaml",
    "govs/G04-角色职责.md",
    "standards/S01-文档编码规范.md",
    "standards/S02-编码规范.md",
    "standards/S03-文档规范.md",
    "standards/S04-质量保证.md",
    "standards/S05-交付控制.md",
    "standards/S06-证据规范.md",
    "standards/S07-合约数据设计.md",
    "standards/S08-可信合规.md",
    "standards/S09-运营韧性.md",
    "1-reqs/requirements.md",
    "2-designs/architecture.md",
    "3-tasks/task-plan.md",
    "tests/test-plan.md",
    "releases/release-plan.md",
    "changelogs/CHANGELOG.md",
    "runbook/runbook.md",
    "meta/agents/agents.md",
    "meta/agents/orchestrator-agent.md",
    "meta/agents/specifier-agent.md",
    "meta/agents/architect-agent.md",
    "meta/agents/planner-agent.md",
    "meta/agents/researcher-agent.md",
    "meta/agents/developer-agent.md",
    "meta/agents/tester-agent.md",
    "meta/agents/release-agent.md",
    "meta/agents/reviewer-agent.md",
    "meta/skills/skills.md",
    "meta/skills/clarify-requirements-skill.md",
    "meta/skills/write-requirements-skill.md",
    "meta/skills/analyze-change-impact-skill.md",
    "meta/skills/analyze-options-skill.md",
    "meta/skills/draft-adr-skill.md",
    "meta/skills/generate-design-skill.md",
    "meta/skills/decompose-tasks-skill.md",
    "meta/skills/fetch-knowledge-skill.md",
    "meta/skills/run-validation-skill.md",
    "meta/skills/generate-changelog-release-skill.md",
    "meta/skills/check-traceability-skill.md",
    "meta/skills/security-compliance-review-skill.md",
    "meta/skills/sync-spec-code-skill.md",
    "meta/skills/request-decision-skill.md",
    "meta/skills/generate-code-skill.md",
    "meta/skills/generate-unit-test-skill.md",
    "meta/skills/generate-acceptance-test-skill.md",
    "meta/skills/maintain-runbook-skill.md",
    "meta/skills/estimate-effort-skill.md",
    "meta/tools/tools.md",
    "meta/tools/user-guide.md",
    "meta/tools/sdd/__init__.py",
    "meta/tools/sdd/config.py",
    "meta/tools/sdd/log.py",
    "meta/tools/sdd/commands/__init__.py",
    "meta/tools/sdd/commands/registry.py",
    "meta/tools/sdd/checkers/__init__.py",
    "meta/tools/sdd/generators/__init__.py",
    "meta/tools/sdd/validators/__init__.py",
    "meta/index/index.md",
    "meta/index/sources.md",
    "meta/index/traceability.md",
    "meta/index/traceability.json",
    "meta/index/agent-dispatch.json",
    "meta/index/tool-adapters.json",
    "meta/index/capability-matrix.md",
]

CATEGORY_DIRECTORY_ROWS = [
    ("治理", "govs"),
    ("标准", "standards"),
    ("需求", "1-reqs"),
    ("决策", "adrs"),
    ("设计", "2-designs"),
    ("任务", "3-tasks"),
    ("测试", "tests"),
    ("发布", "releases"),
    ("变更", "changelogs"),
    ("运行", "runbook"),
    ("Agents", "agents"),
    ("Skills", "skills"),
    ("工具", "tools"),
    ("索引", "meta/index"),
    ("模板", "templates"),
    ("示例", "examples"),
]

DIRECTORIES = [
    "govs",
    "standards",
    "1-reqs",
    "adrs",
    "2-designs",
    "2-designs/api",
    "2-designs/schema",
    "2-designs/architecture",
    "2-designs/tests",
    "3-tasks",
    "tests",
    "releases",
    "changelogs",
    "runbook",
    "agents",
    "skills",
    "tools",
    "meta/index",
    "templates",
    "examples",
]

TEMPLATE_CONTENTS: dict[str, str] = {
    "templates/req.template.md": """# 需求规范模板

## 元信息
- 文档编号：
- 版本：
- 负责人：
- 日期：

## 目标与范围
- 目标：
- 范围：
- 不做：

## 背景与现状
- 问题陈述：
- 业务价值：
- 当前限制：

## 角色与场景
- 角色：
- 场景：
- 业务流程：

## 功能需求
- FR-1：
- FR-2：

## 非功能需求
- 性能：
- 可用性：
- 安全：
- 隐私：
- 可观测性：
- 可维护性：

## 数据与合规
- 数据分类：
- 合规要求：
- 保留与删除：

## 约束与假设
- 技术约束：
- 依赖约束：
- 关键假设：

## 验收标准
- AC-1：
- AC-2：

## 风险与开放问题
- 风险：
- 未决问题：

## 追踪
- 关联 ADR：
- 关联设计：
- 关联任务：
- 关联测试：
""",
    "templates/design.template.md": """# 设计模板

## 元信息
- ID：
- 标题：
- 关联需求：
- 关联 ADR：
- 版本：
- 负责人：
- 日期：

## 目标与范围
- 目标：
- 范围：
- 不做：

## 产出清单
- [ ] API 规范：`specs/2-designs/api/<name>.openapi.yaml`
- [ ] 数据模型：`specs/2-designs/schema/<name>.schema.json`
- [ ] 架构图：`specs/2-designs/architecture/<name>.md`
- [ ] 测试场景：`specs/2-designs/tests/<name>.feature`

## 架构概览
- 系统边界：
- 关键组件：
- 数据流与控制流：

## 接口与契约
- 对外接口：
- 对内接口：
- 错误码与协议：

## 数据设计
- 数据模型：
- 数据生命周期：
- 数据一致性与事务：

## 安全与隐私
- 威胁建模摘要：
- 认证与授权：
- 敏感数据处理：

## 可靠性与性能
- 容量与性能目标：
- 降级与回退：
- 关键路径与瓶颈：

## 可观测性与运维
- 指标：
- 日志：
- 追踪：
- 运行手册：

## 测试与验证
- 关键测试：
- 验收口径：

## 追踪
- 需求覆盖：
- 架构决策：
- 关联任务：
""",
    "templates/adr.template.md": """# ADR 模板

## 元信息
- 标题：
- 状态：提议 / 通过 / 废弃
- 日期：
- 负责人：

## 背景与问题
- 背景：
- 问题：
- 约束：

## 决策驱动因素
- 目标：
- 优先级：
- 关键风险：

## 可选方案
- 方案 A：
- 方案 B：
- 方案 C：

## 决策
- 选择：
- 理由：
- 放弃原因：

## 影响与后果
- 正向影响：
- 负面影响：
- 影响范围：

## 风险与缓解
- 风险：
- 缓解措施：

## 迁移与回滚
- 迁移策略：
- 回滚策略：

## 追踪
- 关联需求：
- 关联设计：
- 关联任务：
- 相关 ADR：
""",
    "templates/task.template.md": """# 任务模板

## 元信息
- 任务编号：
- 标题：
- 负责人：
- 状态：待办 / 进行中 / 完成 / 阻塞
- 计划开始：
- 计划结束：

## 背景与目标
- 背景：
- 目标：

## 范围与排除项
- 范围：
- 不做：

## 依赖与前置条件
- 依赖：
- 前置：

## 实施步骤
- 步骤 1：
- 步骤 2：

## 验收标准
- AC-1：
- AC-2：

## 测试与验证
- 单元测试：
- 集成测试：
- 回归测试：

## 风险与回滚
- 风险：
- 回滚：

## 追踪
- 关联需求：
- 关联设计：
- 关联 ADR：
""",
    "templates/gov.template.md": """# 治理模板

## 元信息
- 版本：
- 生效日期：
- 最后更新：
- 责任人：
- 变更说明：

## 目标与范围
- 目标：
- 适用范围：

## 角色与职责
- 角色：
- 职责：

## 决策与审批
- 决策类型：
- 审批层级：

## 闸门与审计
- 质量闸门：
- 审计频率：

## 例外管理
- 例外条件：
- 期限与补偿控制：
""",
    "templates/standard.template.md": """# 规范模板

## 元信息
- 版本：
- 生效日期：
- 最后更新：
- 责任人：
- 变更说明：

## 目标与范围
- 目标：
- 适用范围：

## 强制要求
- MUST-1：
- MUST-2：

## 检查与验收
- 检查项：
- 验收标准：

## 例外处理
- 例外条件：
- 审批与记录：
""",
    "templates/changelog.template.md": """# 变更模板

## 版本信息
- 版本：
- 日期：
- 发布负责人：

## 变更摘要
- 主要变更：
- 影响范围：

## 风险与回滚
- 风险：
- 回滚方案：

## 验证与指标
- 回归测试：
- 关键指标：

## 追踪
- 关联需求：
- 关联设计：
- 关联 ADR：
- 关联任务：
""",
    "templates/release.template.md": """# 发布模板

## 版本信息
- 版本：
- 日期：
- 发布负责人：

## 发布范围
- 功能范围：
- 影响范围：

## 发布前置条件
- 需求与设计完整：
- 关键测试通过：
- 风险评估完成：

## 发布步骤
1.
2.
3.

## 监控与验证
- 监控指标：
- 验证窗口：

## 回滚策略
- 回滚条件：
- 回滚步骤：

## 审批记录
- Owner 审批：通过 / 拒绝
- reviewer-agent 审批：通过 / 拒绝
- 联签结论：通过 / 拒绝
- 审批时间：
""",
    "templates/runbook.template.md": """# 运行手册模板

## 元信息
- 文档编号：
- 版本：
- 负责人：
- 日期：

## 环境与依赖
- 环境：
- 依赖：

## 启停与回滚
- 启动：
- 停止：
- 回滚：

## 监控与告警
- 指标：
- 告警：

## 故障处理
- 分级：
- 处理流程：

## 追踪
- 关联需求：
- 关联设计：
- 关联任务：
""",
    "templates/test.template.md": """# 测试用例模板

## 元信息
- 用例编号：
- 版本：
- 负责人：
- 日期：

## 目标
- 目标：

## 前置条件
- 前置条件：

## 步骤
1.
2.

## 期望结果
- 期望结果：

## 数据与环境
- 测试数据：
- 环境：

## 优先级与类型
- 优先级：
- 类型：单元/集成/端到端/性能/安全

## 追踪
- 关联需求：
- 关联任务：
""",
}

SEED_CONTENTS: dict[str, str] = {
    "meta/index/index.md": "# specs 总索引\n",
    "meta/index/sources.md": "# 外部来源索引\n",
    "meta/index/traceability.md": "# 追踪矩阵\n",
    "meta/index/traceability.json": "{}\n",
    "meta/index/agent-dispatch.json": "{}\n",
    "meta/index/tool-adapters.json": "{}\n",
    "meta/index/capability-matrix.md": "# 能力矩阵\n",
    "govs/G01-治理与流程.md": "# 治理与流程（严格）\n",
    "govs/G02-项目宪章.md": "# 项目宪章\n",
    "govs/G03-质量门禁.md": "# 质量门禁\n",
    "govs/G05-Agent协作宪章.md": "# agent 协作宪章\n",
    "govs/knowledge-sources.yaml": "knowledge_sources:\n  - name: \"official-docs\"\n    url: \"https://example.com\"\n    scope: [\"architecture\", \"implementation\"]\n\nconstraints:\n  - rule: \"adr-must-reference-sources\"\n    enforcement: \"manual-review\"\n",
    "govs/G04-角色职责.md": "# 角色与职责（严格）\n",
    "standards/S01-文档编码规范.md": "# 文档编码规范\n",
    "standards/S02-编码规范.md": "# 编码规范（严格）\n",
    "standards/S03-文档规范.md": "# 文档规范（严格）\n",
    "standards/S04-质量保证.md": "# 质量与验证规范（严格）\n",
    "standards/S05-交付控制.md": "# 交付与变更控制规范（严格）\n",
    "standards/S06-证据规范.md": "# 证据与知识使用规范（严格）\n",
    "standards/S07-合约数据设计.md": "# 接口与数据设计规范（严格）\n",
    "standards/S08-可信合规.md": "# 安全与合规规范（严格）\n",
    "standards/S09-运营韧性.md": "# 可运行性与韧性规范（严格）\n",
    "1-reqs/requirements.md": "# 需求说明\n",
    "adrs/README.md": "# ADR（架构决策记录）\n",
    "2-designs/architecture.md": "# 架构设计\n",
    "2-designs/api/README.md": "# API 设计产物\n",
    "2-designs/schema/README.md": "# 数据模型产物\n",
    "2-designs/architecture/README.md": "# 架构图产物\n",
    "2-designs/tests/README.md": "# 测试场景产物\n",
    "3-tasks/task-plan.md": "# 任务计划\n",
    "tests/test-plan.md": "# 测试计划\n",
    "releases/release-plan.md": "# 发布计划\n\n## 审批记录\n- Owner 审批：通过 / 拒绝\n- reviewer-agent 审批：通过 / 拒绝\n- 联签结论：通过 / 拒绝\n- 审批时间：\n",
    "changelogs/CHANGELOG.md": "# 变更记录\n",
    "runbook/runbook.md": "# 运行手册（严格）\n",
    "agents/agents.md": "# Agent 角色定义\n",
    "agents/orchestrator-agent.md": "# orchestrator agent\n",
    "agents/specifier-agent.md": "# specifier agent\n",
    "agents/architect-agent.md": "# architect agent\n",
    "agents/planner-agent.md": "# planner agent\n",
    "agents/researcher-agent.md": "# researcher agent\n",
    "agents/release-agent.md": "# release agent\n",
    "agents/developer-agent.md": "# developer agent\n",
    "agents/tester-agent.md": "# tester agent\n",
    "agents/reviewer-agent.md": "# reviewer agent\n",
    "skills/skills.md": "# Skills 使用清单\n",
    "skills/clarify-requirements-skill.md": "# clarify requirements skill\n",
    "skills/write-requirements-skill.md": "# write requirements skill\n",
    "skills/analyze-change-impact-skill.md": "# analyze change impact skill\n",
    "skills/analyze-options-skill.md": "# analyze options skill\n",
    "skills/draft-adr-skill.md": "# draft adr skill\n",
    "skills/generate-design-skill.md": "# generate design skill\n",
    "skills/decompose-tasks-skill.md": "# decompose tasks skill\n",
    "skills/fetch-knowledge-skill.md": "# fetch knowledge skill\n",
    "skills/run-validation-skill.md": "# run validation skill\n",
    "skills/generate-changelog-release-skill.md": "# generate changelog release skill\n",
    "skills/check-traceability-skill.md": "# check traceability skill\n",
    "skills/security-compliance-review-skill.md": "# security compliance review skill\n",
    "skills/sync-spec-code-skill.md": "# sync spec code skill\n",
    "skills/request-decision-skill.md": "# request decision skill\n",
    "skills/generate-code-skill.md": "# generate code skill\n",
    "skills/generate-unit-test-skill.md": "# generate unit test skill\n",
    "skills/generate-acceptance-test-skill.md": "# generate acceptance test skill\n",
    "skills/maintain-runbook-skill.md": "# maintain runbook skill\n",
    "skills/estimate-effort-skill.md": "# estimate effort skill\n",
    "tools/tools.md": "# 工具链与执行规范\n",
    "tools/user-guide.md": "# 工具使用手册\n",
    "tools/requirements.txt": "# 当前工具仅依赖 Python 标准库\n",
    "tools/sdd/__init__.py": "\"\"\"SDD 工具包根模块。\"\"\"\n",
    "tools/sdd/config.py": "\"\"\"SDD CLI 配置常量与初始化模板内容。\"\"\"\n",
    "tools/sdd/log.py": "\"\"\"统一日志输出工具。\"\"\"\n",
    "tools/sdd/commands/__init__.py": "\"\"\"SDD 命令注册子包。\"\"\"\n",
    "tools/sdd/commands/registry.py": "\"\"\"CLI 子命令注册器。\"\"\"\n",
    "tools/sdd/checkers/__init__.py": "\"\"\"SDD 检查器子包。\"\"\"\n",
    "tools/sdd/generators/__init__.py": "\"\"\"SDD 生成器子包。\"\"\"\n",
    "tools/sdd/validators/__init__.py": "\"\"\"SDD 校验器子包。\"\"\"\n",
}
