# commands module

当前由 `sdd/cli.py` 统一注册命令，命令分组如下：
- `create-*`：创建工件并自动刷新索引。
- `check-*`：执行基线、治理、依赖、质量、完整性、命名、漂移等检查。
- `validate-*`：执行需求与设计文档校验。
- `generate-*`：生成索引、追溯矩阵、调度规则与工具入口（`generate-index`、`generate-traceability-matrix`、`generate-agent-dispatch`、`generate-tool-adapters`）。
- `resolve-*`：基于 Agent/Skill 映射解析任务调度建议（`resolve-agent-dispatch`）。
- `*-tool-adapter*`：管理工具适配清单（`list-tool-adapters`、`add-tool-adapter`、`remove-tool-adapter`）。
