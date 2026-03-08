# Skills 使用清单

## 元信息
- 版本：v1.2
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：补充可选依赖与质量指标字段，保持轻量化治理。

## 说明
- 本目录定义可复用的 SDD 能力单元，用于标准化常见任务执行方式。
- Skill 输出必须可复核、可追踪、可回填。

## Skill 索引
- `clarify-requirements-skill.md`：需求澄清与边界固化。
- `write-requirements-skill.md`：结构化需求编写。
- `analyze-options-skill.md`：多方案比较与取舍分析。
- `analyze-change-impact-skill.md`：变更影响范围与回归范围评估。
- `request-decision-skill.md`：标准化决策请求与确认。
- `draft-adr-skill.md`：ADR 草案编制。
- `generate-design-skill.md`：架构与详细设计产出。
- `decompose-tasks-skill.md`：任务分解与依赖梳理。
- `estimate-effort-skill.md`：任务工作量估算与排期建议。
- `fetch-knowledge-skill.md`：知识检索与证据整理。
- `generate-code-skill.md`：按规格生成代码骨架。
- `generate-unit-test-skill.md`：按代码与设计生成单元测试骨架。
- `generate-acceptance-test-skill.md`：按验收标准生成验收测试用例。
- `maintain-runbook-skill.md`：运维手册维护与发布回填。
- `run-validation-skill.md`：门禁校验执行与汇总。
- `generate-changelog-release-skill.md`：发布记录与变更日志生成。
- `check-traceability-skill.md`：追踪链路完整性检查。
- `security-compliance-review-skill.md`：安全与合规专项审查。
- `sync-spec-code-skill.md`：规范与实现漂移检测。

## 使用要求
- 每个 Skill 必须包含：能力描述、使用场景、输入/输出格式、执行步骤、约束条件。
- Skill 执行结果应在对应 spec 工件中落地。

## 结构字段规范
- `执行方式` 为可选字段。
- `dependencies` 为可选字段，用于声明显式前置 Skill 或必要输入条件。
- `quality-metrics` 为可选字段，用于声明结果质量判定口径（如完整性、准确性、时效性）。
- 当 Skill 需要给出可复用工具命令索引时，必须使用 `执行方式` 字段。
- 未涉及稳定命令索引的 Skill 可省略 `执行方式`，不视为结构缺失。
- `执行方式` 仅描述建议命令与用途，不改变 Agent 审批与决策边界。

## Skill 前置输出约定
- 如存在显式上游依赖，可在 `输入格式` 中增加 `前置 Skill 输出（可选）`。
- 前置输出仅用于复用分析结果，不转移责任归属；最终结论仍由当前调用 Agent 复核签收。

## 边界声明
- Skill 是标准化能力单元，不是角色替代品。
- Skill 只定义“怎么做”，不定义“谁负责最终决策”。
- 任何 Skill 结果进入正式文档前，必须由对应 Agent 复核并签收。
- Skill 执行结果不等同于发布放行，发布审批由治理角色链路决定。

## 责任映射维护规则
- Agent-Skill 权威映射仅维护在 `specs/meta/agents/agents.md`。
- 本文仅维护 Skill 索引、使用边界与执行约束，避免重复维护导致漂移。

## 版本兼容策略
- 不维护逐项 Agent-Skill 版本兼容矩阵，避免与 `specs/meta/agents/agents.md` 形成双份事实源并引入漂移。
- 兼容性以同主版本协作为默认前提（如 `v1.x` 对 `v1.x`），跨主版本变更需通过治理评审并更新约束说明。
