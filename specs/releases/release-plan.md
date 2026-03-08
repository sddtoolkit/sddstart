# 发布计划

## 元信息
- 版本：v1.0.0
- 负责人：release-agent
- 日期：2026-03-02

## 发布范围
- 包含内容：主工件内容补齐、追踪实体校验能力、需求与设计边界标准。
- 不包含内容：业务域功能开发与外部服务集成。

## 依赖与前置条件
- 依赖：req-baseline-001，dsn-baseline-architecture，tsk-baseline-001，test-baseline-001。
- 前置检查：`check-status`、`check-completeness`、`check-naming`、`validate-requirement`、`validate-design` 全通过。

## 发布步骤
- 步骤：冻结规格文档 -> 运行检查 -> 更新索引与追踪 -> 归档发布记录。
- 验证：检查退出码为 0，索引包含新增标准文档与任务/测试工件。

## 回滚方案
- 触发条件：发布后发现阻断级文档逻辑冲突或关键检查误判。
- 回滚步骤：回退到上一版本发布记录并恢复对应文档版本，重新执行门禁检查。

## 风险与沟通
- 风险：规则收紧导致下游模板仓库适配工作增加。
- 通知对象：Owner、reviewer-agent、项目模板维护者。

## 审批记录
- Owner 审批：通过 / 拒绝
- reviewer-agent 审批：通过 / 拒绝
- 联签结论：通过 / 拒绝
- 审批时间：2026-03-02

## 追踪
- 关联需求：req-baseline-001
- 关联任务：tsk-baseline-001
- 关联变更：changelog-20260302-governance-baseline
