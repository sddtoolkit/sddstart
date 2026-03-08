# 运行手册：需求变更处理

## 元信息
- 文档编号：runbook-requirement-change-001
- 版本：v1.0
- 负责人：orchestrator-agent
- 日期：2026-03-02

## 触发条件
- 新增/调整业务目标或验收标准。
- 发现需求与设计/实现不一致。

## 执行步骤
1. 在需求文档中登记变更动机、范围与影响。
2. 更新追踪关系（REQ -> DSN/TSK/TEST）。
3. 若涉及重大取舍，新增或更新 ADR。
4. 执行 `check-status`、`validate-requirement`、`check-completeness`。
5. 更新 changelog 与发布评估结论。

## 门禁要求
- 未完成影响评估不得进入 DS-Gate。
- 需求变更必须有可测试验收标准。

## 回滚策略
- 回滚到上一版需求并恢复对应追踪链路。
- 重新评审后再进入下一阶段。
