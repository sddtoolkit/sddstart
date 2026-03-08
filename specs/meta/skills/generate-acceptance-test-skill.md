# generate acceptance test skill

## 元信息
- 版本：v1.0
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：从通用测试生成能力拆分，明确测试侧验收用例职责。

## 能力描述
- 基于需求验收标准与设计约束生成验收测试用例，覆盖业务主流程与关键风险场景。

## 使用场景
- 需求或设计评审通过后建立验收测试基线。
- 发布前补齐关键验收场景与回归场景。

## 输入格式
- 验收标准（Given/When/Then）、设计约束、风险清单。

## 输出格式
- 验收测试用例（场景、前置、步骤、预期）。
- 用例优先级与风险标签。
- 与 REQ/DSN/TSK/TEST 的追溯关系。

## 执行步骤
1. 提取需求验收口径与边界条件。
2. 生成主流程、异常流程与边界流程场景。
3. 标注优先级并对齐回归范围。
4. 输出用例清单并登记追溯关系。

## 执行方式
- 追溯生成命令：`python3 specs/meta/tools/sddtool.py generate-traceability-matrix`
- 完整性检查命令：`python3 specs/meta/tools/sddtool.py check-completeness`

## 约束条件
- 本 Skill 仅生成测试用例，不替代测试执行结论与发布放行决策。
- 最终验证结论由 tester-agent 输出，reviewer-agent 复核。
