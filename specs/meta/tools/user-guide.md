# 工具使用手册

## 快速开始（5 分钟）
1. 初始化：`python3 specs/meta/tools/sddtool.py initialize`
2. 生成索引：`python3 specs/meta/tools/sddtool.py generate-index`
3. 生成追踪矩阵：`python3 specs/meta/tools/sddtool.py generate-traceability-matrix`
4. 生成调度规则：`python3 specs/meta/tools/sddtool.py generate-agent-dispatch`
5. 同步工具入口：`python3 specs/meta/tools/sddtool.py generate-tool-adapters`
6. 执行主检查：`python3 specs/meta/tools/sddtool.py check-status`
7. 执行链路检查：`python3 specs/meta/tools/sddtool.py check-completeness`

## 常用命令速查
- 创建工件：`create-requirement/create-design/create-adr/create-task/create-test/create-release`
- 生成工件：`generate-index/generate-traceability-matrix/generate-agent-dispatch/generate-tool-adapters`
- 校验工件：`validate-requirement/validate-design`
- 检查工件：`check-status/check-governance/check-completeness/check-naming/check-changelog/check-drift`
- **质量门禁**：`check-quality-gates` (聚合所有校验，建议发布前执行)
- **开发者辅助**：
  - `bundle-task-context <TASK_ID>` (聚合任务关联的所有文档到 tmp/)
  - `trace-code <FILE_PATH>` (从代码文件反向追溯规范来源)
  - `version` (显示体系与工具版本)
- 调度解析：`resolve-agent-dispatch --task <描述> [--stage <阶段>] [--skills <skill>] [--json]`
- 适配管理：`list-tool-adapters`、`add-tool-adapter`、`remove-tool-adapter`

## 常见错误与排查
- 错误：`主工件存在占位或缺失内容`
  - 处理：补齐对应文档章节中的关键字段（如版本、负责人、目标、追踪项）。
- 错误：`关联的设计/任务/测试不存在`
  - 处理：确认追踪 ID 已在对应目录真实出现，并重新生成追踪矩阵。
- 错误：`未在索引登记`
  - 处理：执行 `generate-index` 并确认文件在 `specs/meta/index/index.md` 的“文件”章节。
- 错误：`命名不规范`
  - 处理：按 `specs/standards/S01-文档编码规范.md` 重命名后重试。

## 推荐执行顺序
1. 先执行 `check-status`，确保主工件有实质内容。
2. 再执行 `validate-requirement`、`validate-design`，检查章节与字段。
3. 执行 `generate-traceability-matrix` 后执行 `check-completeness`。
4. 最后执行 `check-naming`、`check-governance`、`check-changelog`。

## 跨工具统一调度（Codex/Claude/Kimi/Kiro/Crush/OpenCode）
1. 先执行 `python3 specs/meta/tools/sddtool.py generate-agent-dispatch`，生成统一规则文件。
2. 执行 `python3 specs/meta/tools/sddtool.py generate-tool-adapters`，同步入口文件与适配清单。
3. 工具收到任务后执行 `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task "<任务描述>" --json`。
4. 读取输出中的 `primary_agent` 与 `recommended_skills`，按同一规则执行，避免不同工具调度漂移。

## 增减工具适配
1. 新增工具（示例 OpenCode）：
   `python3 specs/meta/tools/sddtool.py add-tool-adapter opencode \"OpenCode\" --entry-file AGENTS.md --entry-format markdown --shared-entry`
2. 查看清单：
   `python3 specs/meta/tools/sddtool.py list-tool-adapters`
3. 移除工具（示例 Claude Code）：
   `python3 specs/meta/tools/sddtool.py remove-tool-adapter claude-code`
4. 若被移除工具是某共享入口最后一个引用，命令会自动回收该入口文件。

## CI 集成建议
- PR 阶段至少执行：
  - `check-status`
  - `validate-requirement`
  - `validate-design`
  - `check-completeness`
  - `check-naming`
- 发布前增加：
  - `check-governance`
  - `check-changelog`
  - `check-drift`
