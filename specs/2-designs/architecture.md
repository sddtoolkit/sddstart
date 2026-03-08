# 架构设计

## 元信息
- 文档编号：dsn-baseline-architecture
- 版本：v1.0
- 负责人：architect-agent
- 日期：2026-03-02

## 系统边界
- 边界定义：仅覆盖 `specs/` 与 `specs/meta/tools/sdd/` 的文档与校验逻辑，不涉及业务应用运行时。
- 外部依赖：Python 3 标准库、文件系统、GitHub Actions 执行环境。

## 模块划分
- 组件列表：CLI 注册层、handlers 执行层、checkers/validators/generators 功能层、配置与 IO 公共层。
- 责任边界：CLI 只做参数路由；handlers 负责流程编排；功能层负责单一检查或生成逻辑。

## 数据流与控制流
- 关键流程：命令输入 -> 参数解析 -> handler -> 文档读写/检查 -> 日志输出 -> 退出码。
- 数据流向：`specs/*.md` 被读取校验；`meta/index/index.md` 与 `traceability.md/json` 被生成更新。

## 接口列表
- 对外接口：`python3 specs/meta/tools/sddtool.py <subcommand>`。
- 对内接口：`sdd.handlers.commands` 调用 `sdd.checkers|validators|generators` 的模块函数。

## 运行时与部署
- 拓扑结构：本地 CLI 与 CI Runner 均单进程执行，无常驻服务。
- 运行约束：工具只允许在仓库目录内操作 `specs/`，拒绝绝对路径与越界路径。

## 安全与隐私
- 认证与授权：通过仓库权限控制执行人，发布放行需 Owner 与 reviewer-agent 联签。
- 数据保护：所有文档 UTF-8 存储；外部来源必须登记，禁止不明来源事实入库。

## 可靠性与性能
- 容量与性能目标：模板规模下所有检查命令应在 5 秒内完成并输出可定位错误。
- 降级与回滚：规则升级导致阻断时，允许先修文档再执行命令，不以跳过检查作为回滚策略。

## 可观测性与运维
- 指标与日志：统一 `INFO/WARN/ERROR` 输出，错误信息需包含路径与缺失项。
- 运维流程：每次规范变更后执行 `check-status/check-completeness/check-naming` 并记录结果。

## 风险与权衡
- 风险：校验增强可能提升初期维护成本，需配套模板与示例文档。
- 权衡：优先保证文档质量可审计性，接受少量写作成本上升。

## 追踪
- 关联需求：req-baseline-001
- 关联 ADR：adr-20260302-baseline-governance
- 关联任务：tsk-baseline-001
