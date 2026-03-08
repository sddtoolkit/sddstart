# maintain runbook skill

## 元信息
- 版本：v1.1
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：统一角色命名为 developer-agent。

## 能力描述
- 维护 `runbook` 运维手册，确保上线、回滚、故障处置与发布变更保持一致。

## 使用场景
- 新功能上线前更新运维步骤与监控项。
- 故障复盘后回填处置流程与防复发措施。
- 发布计划变更后同步运行手册。

## 输入格式
- 发布计划、变更清单、故障复盘记录、监控告警策略。

## 输出格式
- 更新后的 `runbook/runbook.md`。
- 运维变更摘要与关联发布记录。
- 待确认风险与演练清单。

## 执行步骤
1. 汇总发布变更对运维的影响。
2. 更新启动/停止/回滚/应急步骤。
3. 同步监控指标、告警阈值与联系人信息。
4. 关联需求、设计、任务与变更记录。

## 执行方式
- 发布文档命令：`python3 specs/meta/tools/sddtool.py create-release <version>`
- 索引刷新命令：`python3 specs/meta/tools/sddtool.py generate-index`

## 约束条件
- 本 Skill 只维护运行手册与回填内容，不拥有发布审批权。
- developer-agent 负责技术细节输入，release-agent 负责最终归档与发布同步。
