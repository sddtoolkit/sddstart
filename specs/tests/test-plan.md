# 测试计划

## 元信息
- 文档编号：tp-baseline-001
- 版本：v1.0
- 负责人：tester-agent
- 日期：2026-03-02

## 目标与范围
- 目标：验证 SDD 工具链在内容质量与追踪完整性上的阻断能力。
- 范围：`validate-requirement`、`validate-design`、`check-status`、`check-completeness`、`check-naming`。
- 不做：业务代码功能测试与性能压测。

## 策略与层级
- 单元测试：覆盖 validators/checkers 新增规则与边界条件。
- 集成测试：通过 CLI 命令联调主工件校验与追踪生成流程。
- 端到端测试：模拟从需求到发布文档回填并执行全套检查。
- 性能/安全测试：验证路径越界拦截与基础执行性能阈值。

## 覆盖与数据
- 覆盖范围：REQ/DSN/TASK/TEST/REL/CHANGELOG/RUNBOOK 七类主工件。
- 数据准备：使用模板仓库内基线文档与构造的错误样例。
- 环境要求：Python 3.10+，UTF-8 文件系统。

## 门槛与验收
- 通过标准：所有检查命令退出码为 0，且无占位字段告警。
- 退出条件：阻断项全部清零并完成追踪矩阵回填。

## 风险与回滚
- 风险：检查规则升级导致旧项目集中报错。
- 回滚策略：保留规则变更记录，按文档分批整改，不回退已通过治理评审的规则。

## 追踪
- 关联需求：req-baseline-001
- 关联设计：dsn-baseline-architecture
- 关联任务：tsk-baseline-001
