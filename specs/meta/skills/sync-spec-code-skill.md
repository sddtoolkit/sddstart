# sync spec code skill

## 元信息
- 版本：v1.2
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：对齐 check-drift 的标记检查机制与扫描范围。

## 能力描述
- 检测规格文档与实现代码之间的漂移并给出回填建议。

## 使用场景
- 代码评审阶段的一致性检查。
- 发布前核验 spec 与实现同步状态。

## 输入格式
- 需求、设计、任务、测试、代码变更信息。

## 输出格式
- 漂移项清单（来源标记缺失、追溯断链、需人工复核项）。
- 回填建议（修 spec / 修实现 / 补证据）。

## 执行步骤
1. 运行 `check-drift`，检查 `src/` 下 `.ts/.js/.go/.py/.rs` 文件是否包含 `GENERATED FROM SPEC` 标记。
2. 运行追溯矩阵生成与完整性检查，识别 REQ 链路缺口。
3. 合并代码来源标记结果与文档追溯结果，标注阻断项与告警项。
4. 输出漂移报告并回填整改项。

## 执行方式
- 漂移检查命令：`python3 specs/meta/tools/sddtool.py check-drift`
- 追溯矩阵命令：`python3 specs/meta/tools/sddtool.py generate-traceability-matrix`
- 链路完整性命令：`python3 specs/meta/tools/sddtool.py check-completeness`

## 约束条件
- 本 Skill 仅提供检测与建议，不做最终发布决策。
- 本 Skill 聚焦文档与实现的一致性漂移，不替代文档间追溯完整性审计。
- 当前工具层面仅提供“来源标记存在性”静态检查，不直接给出代码语义级覆盖结论。
