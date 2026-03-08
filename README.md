# sddstart

一个可直接发布为 GitHub Template Repository 的 SDD（Spec-Driven Development）项目骨架。

## 模板包含内容

- `specs/govs`：治理、角色、评审、审计政策
- `specs/standards`：命名、文档、质量、安全、测试等标准
- `specs/1-reqs`、`specs/2-designs`、`specs/3-tasks`：SDD 主阶段目录
- `specs/adrs`、`specs/tests`、`specs/releases`、`specs/changelogs`：跨阶段支撑工件目录
- `specs/templates`：需求/设计/ADR/任务/测试/发布模板
- `specs/meta/tools`：创建与校验脚本
- `specs/meta/index`：总索引、来源索引、追踪矩阵

## 新项目使用流程

1. 在 GitHub 上使用 `Use this template` 创建新仓库。
2. 初始化或补齐 `specs`（幂等）：

```bash
python3 specs/meta/tools/sddtool.py initialize
```

3. 按需创建工件：

```bash
python3 specs/meta/tools/sddtool.py create-requirement <scope>
python3 specs/meta/tools/sddtool.py create-design <module>
python3 specs/meta/tools/sddtool.py create-adr <topic>
python3 specs/meta/tools/sddtool.py create-task <scope> <id>
python3 specs/meta/tools/sddtool.py create-test <scope> <id>
python3 specs/meta/tools/sddtool.py create-release <version>
```
- 创建命令执行后会自动刷新 `specs/meta/index/index.md`。
- 需要机器可读追溯时执行：

```bash
python3 specs/meta/tools/sddtool.py generate-traceability-matrix
```

4. 完成内容回填后执行检查：

```bash
python3 specs/meta/tools/sddtool.py check-status
python3 specs/meta/tools/sddtool.py check-governance
python3 specs/meta/tools/sddtool.py check-dependencies
python3 specs/meta/tools/sddtool.py check-code-quality
python3 specs/meta/tools/sddtool.py check-completeness
python3 specs/meta/tools/sddtool.py validate-requirement
python3 specs/meta/tools/sddtool.py validate-design
python3 specs/meta/tools/sddtool.py check-changelog
python3 specs/meta/tools/sddtool.py check-naming
python3 specs/meta/tools/sddtool.py check-drift
```

## 工具依赖

- Python 依赖统一放在 `specs/meta/tools/requirements.txt`。
- 当前版本仅使用 Python 标准库，无需额外安装。
- Windows 可使用 `py -3` 替代 `python3` 执行命令。

## 发布模板建议

- 开启仓库的 `Template repository` 选项。
- 保护主分支并要求 CI 通过。
- 每次模板升级同步更新 `specs/changelogs/CHANGELOG.md`。
