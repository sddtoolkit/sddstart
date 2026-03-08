# 运行手册（严格）

## 元信息
- 文档编号：runbook-baseline-001
- 版本：v1.0
- 负责人：release-agent
- 日期：2026-03-02

## 目标与范围
- 目标：确保上线、运维与故障处理有一致的执行指南。
- 适用范围：部署、监控、回滚、故障响应与恢复。

## 环境与依赖
- 运行环境：本地开发环境与 CI Runner（Linux）。
- 关键依赖：Python 3.10+，仓库写权限，UTF-8 文件系统。
- 权限与访问：仅允许维护者修改 `specs/` 与工具代码。

## 启动与停止
- 启动步骤：拉取仓库后执行 `python3 specs/meta/tools/sddtool.py check-status`。
- 停止步骤：停止 CI 任务并冻结当前变更分支。
- 回滚步骤：回退到上一版本文档与工具提交后重新执行门禁检查。

## 监控与告警
- 关键指标：检查命令退出码、阻断项数量、追踪矩阵条目数。
- 告警阈值：任一强制检查返回非 0 即触发阻断告警。
- 处置流程：定位失败文件 -> 修复文档/工具 -> 复跑检查 -> 回填 changelog。

## 故障与应急
- 故障分级：P0（发布阻断）、P1（链路缺失）、P2（格式不一致）。
- 应急联系人与职责：reviewer-agent 负责审计结论，release-agent 负责执行回滚。
- 临时缓解措施：冻结发布并创建整改任务，禁止绕过门禁直接放行。

## 变更与发布
- 变更前置检查：确保需求、设计、任务、测试、发布文档均已回填。
- 发布步骤：执行检查 -> 更新索引与追踪 -> 更新发布记录与变更记录。
- 验证清单：`check-status`、`check-completeness`、`check-naming` 全通过。
- 场景手册：需求变更见 `runbook-requirement-change.md`；设计回退见 `runbook-design-rollback.md`；紧急发布见 `runbook-emergency-release.md`。

## 追踪
- 关联需求：req-baseline-001
- 关联设计：dsn-baseline-architecture
- 关联任务：tsk-baseline-001
- 关联变更：changelog-20260302-governance-baseline
