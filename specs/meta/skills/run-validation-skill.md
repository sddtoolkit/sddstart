# run validation skill

## 元信息
- 版本：v1.1
- 生效日期：2026-02-28
- 最后更新：2026-03-02
- 变更说明：对齐 sddtool.py 各校验命令的实际语义与执行顺序。


## 能力描述
- 编排并执行 sddtool.py 校验命令，输出可审计的门禁事实与阻断项。

## 使用场景
- 里程碑前自检、发布前门禁、评审前质量核验。

## 输入格式
- 校验范围（全量/增量）。
- 当前分支或版本上下文。

## 输出格式
- 校验结果摘要（通过/失败）。
- 失败项清单与修复建议。

## 执行步骤
1. 运行 `check-status`。
2. 运行 `validate-requirement`、`validate-design`、`check-changelog`、`check-naming`。
3. 运行 `check-governance`、`check-dependencies`、`check-code-quality`、`check-completeness`、`check-drift`。
4. 输出可追溯报告（区分错误阻断与告警项）。

## 执行方式
- `python3 specs/meta/tools/sddtool.py check-status`
- `python3 specs/meta/tools/sddtool.py check-governance`
- `python3 specs/meta/tools/sddtool.py check-dependencies`
- `python3 specs/meta/tools/sddtool.py check-code-quality`
- `python3 specs/meta/tools/sddtool.py check-completeness`
- `python3 specs/meta/tools/sddtool.py validate-requirement`
- `python3 specs/meta/tools/sddtool.py validate-design`
- `python3 specs/meta/tools/sddtool.py check-changelog`
- `python3 specs/meta/tools/sddtool.py check-naming`
- `python3 specs/meta/tools/sddtool.py check-drift`

## 约束条件
- 不得跳过强制门禁。
- 校验失败时不得给出放行结论。
- 本 Skill 仅输出校验事实，不承担发布审批。
- `check-status` 仅校验必需文件“存在且非空”。
- `validate-requirement` 与 `validate-design` 当前只校验主文档（`1-reqs/requirements.md`、`2-designs/architecture.md`）。
- `check-completeness` 会先刷新追溯矩阵，再执行 REQ 链路检查。
