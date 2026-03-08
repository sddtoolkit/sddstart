# 能力矩阵

## 元信息
- 版本：v1.0
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：补齐治理基线文档与校验能力对齐说明。

## 字段说明
- 优先级：`P0` 核心必备，`P1` 重要增强，`P2` 按需扩展。
- 成熟度：`L1` 已定义，`L2` 可重复，`L3` 可度量，`L4` 持续优化。

## 维护机制
- `specs/meta/index/index.md`：由 `python3 specs/meta/tools/sddtool.py generate-index` 自动生成。
- `specs/meta/index/traceability.md` / `traceability.json`：由 `python3 specs/meta/tools/sddtool.py generate-traceability-matrix` 自动生成。
- `specs/meta/index/capability-matrix.md`：人工维护，变更后必须执行 `generate-index` 与 `check-completeness` 防漂移。

## 治理能力
| 能力 | 文档 | 优先级 | 成熟度 | Owner | 依赖 | 状态 |
|---|---|---|---|---|---|---|
| 治理总览 | `govs/G01-治理与流程.md` | P0 | L2 | reviewer-agent | G04 / G03 | 生效 |
| 质量门禁 | `govs/G03-质量门禁.md` | P0 | L2 | reviewer-agent | requirements/design/test/release | 生效 |
| 角色与职责 | `govs/G04-角色职责.md` | P0 | L2 | reviewer-agent | agents/agents.md | 生效 |
| 综合质量门禁 | `govs/G03-质量门禁.md` | P0 | L3 | orchestrator-agent | sddtool check-quality-gates | 生效 |
| 一键上下文聚合 | `tools/tools.md` | P1 | L3 | developer-agent | sddtool bundle-task-context | 生效 |
| 代码反向追溯 | `standards/S06-证据规范.md` | P1 | L3 | reviewer-agent | sddtool trace-code | 生效 |

## Agent 能力
| Agent | 主责能力 | 优先级 | 成熟度 | 依赖 Skill | 状态 |
|---|---|---|---|---|---|
| orchestrator-agent | 阶段编排与门禁推进 | P0 | L2 | check-traceability-skill, request-decision-skill | 生效 |
| specifier-agent | 需求结构化与验收定义 | P0 | L2 | clarify-requirements-skill, write-requirements-skill | 生效 |
| architect-agent | 方案评估与架构决策 | P0 | L2 | analyze-options-skill, draft-adr-skill | 生效 |
| planner-agent | 任务分解与依赖管理 | P0 | L2 | decompose-tasks-skill, estimate-effort-skill, analyze-change-impact-skill | 生效 |
| developer-agent | 实现与回填 | P0 | L2 | generate-code-skill, generate-unit-test-skill, run-validation-skill（自检） | 生效 |
| tester-agent | 门禁验证结论 | P0 | L2 | generate-acceptance-test-skill, run-validation-skill | 生效 |
| reviewer-agent | 审计、追溯与合规审查 | P0 | L2 | check-traceability-skill, sync-spec-code-skill, security-compliance-review-skill | 生效 |
| release-agent | 发布执行与归档 | P0 | L2 | generate-changelog-release-skill, maintain-runbook-skill, analyze-change-impact-skill | 生效 |
| researcher-agent | 证据检索与来源核验 | P1 | L2 | fetch-knowledge-skill | 生效 |

## Skill 能力
| Skill | 主责 Agent | 优先级 | 成熟度 | 依赖 | 状态 |
|---|---|---|---|---|---|
| clarify-requirements-skill | specifier-agent | P0 | L2 | requirements.md | 生效 |
| draft-adr-skill | architect-agent | P0 | L2 | adrs | 生效 |
| run-validation-skill | tester-agent | P0 | L2 | check-* 命令 | 生效 |
| security-compliance-review-skill | reviewer-agent | P0 | L1 | governance.md | 生效 |
| request-decision-skill | orchestrator-agent | P1 | L1 | governance.md / roles.md | 生效 |
| estimate-effort-skill | planner-agent | P1 | L1 | task-plan.md | 生效 |
| generate-code-skill | developer-agent | P1 | L1 | design / task / standards | 生效 |
| generate-unit-test-skill | developer-agent | P1 | L1 | code / design / task | 生效 |
| generate-acceptance-test-skill | tester-agent | P1 | L1 | requirements / designs / tests | 生效 |
| maintain-runbook-skill | release-agent | P1 | L1 | runbook.md / release-plan.md | 生效 |
| sync-spec-code-skill | reviewer-agent | P1 | L1 | traceability.md / traceability.json | 生效 |
| analyze-change-impact-skill | planner-agent | P1 | L1 | traceability.md / traceability.json | 生效 |
| fetch-knowledge-skill | researcher-agent | P1 | L2 | knowledge-sources.yaml | 生效 |
