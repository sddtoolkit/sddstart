# check traceability skill

## 元信息
- 版本：v1.2
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：对齐 check-completeness 的实际校验范围与告警口径。


## 能力描述
- 检查 REQ 到 ADR/DSN/TSK/TEST 的文档追溯链路完整性。

## 使用场景
- 里程碑评审、发布前审计、变更影响评估。

## 输入格式
- 需求文档、设计文档、任务计划、测试计划、追踪矩阵。

## 输出格式
- 断链清单。
- 缺失映射项。
- 修复建议与优先级。

## 执行步骤
1. 运行追溯矩阵生成，汇总文档内 REQ/ADR/DSN/TSK/TEST 标识。
2. 检查每个 REQ 是否具备 DSN/TSK/TEST 关联（缺失为错误）。
3. 检查 REQ 的 ADR 关联（缺失为告警，非阻断错误）。
4. 输出修复清单并跟踪闭环。

## 执行方式
- 追溯矩阵生成：`python3 specs/meta/tools/sddtool.py generate-traceability-matrix`
- 链路完整性检查：`python3 specs/meta/tools/sddtool.py check-completeness`

## 约束条件
- 关键需求断链必须阻断发布。
- 修复建议需可执行并可验证。
- 本 Skill 聚焦文档工件之间的追溯链路，不负责代码实现一致性漂移判定。
- 当前工具命令不直接校验发布文档中的审批字段与状态一致性，此类检查由治理命令与人工评审补充。
