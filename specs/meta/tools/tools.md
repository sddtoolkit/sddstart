# 工具链与执行规范

## 工具清单
- 主程序入口：`sddtool.py`
- 使用手册：`user-guide.md`
- 核心实现：`sdd/cli.py`
- 命令文档：`sdd/commands/readme.md`
- 内部模块：`sdd/validators/`、`sdd/generators/`、`sdd/checkers/`、`sdd/handlers/`、`sdd/utils.py`
- 初始化：`initialize`
- 索引生成：`generate-index`
- 追溯矩阵：`generate-traceability-matrix`
- 调度规则：`generate-agent-dispatch`
- 工具适配：`generate-tool-adapters`
- 文档创建：`create-requirement`、`create-design`、`create-adr`、`create-task`、`create-test`、`create-release`
- 检查命令：`check-status`、`check-governance`、`check-dependencies`、`check-code-quality`、`check-completeness`、`validate-requirement`、`validate-design`、`check-changelog`、`check-naming`、`check-drift`
- 调度解析：`resolve-agent-dispatch`
- 适配清单管理：`list-tool-adapters`、`add-tool-adapter`、`remove-tool-adapter`

## 多工具适配清单（权威入口）
- 机器可读清单：`specs/meta/index/tool-adapters.json`
- 统一调度契约：`specs/meta/index/agent-dispatch.json`

| 工具 | Tool ID | 入口文件 | 入口格式 | 共享/独立 | Agent/Skill 定义方式 |
|---|---|---|---|---|---|
| Codex | `codex` | `AGENTS.md` | `markdown` | 共享（与 Kiro/Kimi） | `specs/meta/agents/agents.md` + `specs/meta/skills/skills.md` + `resolve-agent-dispatch` |
| Kiro | `kiro` | `AGENTS.md` | `markdown` | 共享（与 Codex/Kimi） | 同上 |
| Claude Code | `claude-code` | `CLAUDE.md` | `markdown` | 独立 | 同上 |
| Kimi Code | `kimi-code` | `AGENTS.md` | `markdown` | 共享（与 Codex/Kiro） | 同上 |
| Crush | `crush` | `CRUSH.md` + `.crush/init` | `markdown` + `crush-init` | 独立 | 同上（含 init 引导） |
| OpenCode | `opencode` | `AGENTS.md` | `markdown` | 共享（与 Codex/Kiro/Kimi） | 同上 |

说明：
- 共享入口文件删除策略：`remove-tool-adapter` 会先移除工具引用，若该入口不再被任何工具引用，才自动删除入口文件。
- 增减工具无需手改入口文件：使用 `add-tool-adapter` / `remove-tool-adapter` 后执行 `generate-tool-adapters` 即可完成格式转换与同步。

## 证据来源
- 允许的外部资料库：见 `specs/standards/S06-证据规范.md`
- 禁止的来源：任何未登记在 `specs/meta/index/sources.md` 的外部来源

## 执行策略
- 所有检查脚本必须在发布前通过。
- 检查命令不自动写入 `specs/changelogs/`，由 `reviewer-agent` 或 `release-agent` 根据流程回填。
- `specs/meta/tools/requirements.txt` 存放工具依赖（当前仅标准库）。
- 对外调用命令保持不变：`python3 specs/meta/tools/sddtool.py <subcommand>`。
- `sddtool.py check-naming` 同时检查命名规范与索引登记（`meta/index/index.md`）。
- `create-*` 命令在创建文档后会自动刷新索引。
- `generate-index` 会输出文档总览表与核心能力清单。
- `generate-traceability-matrix` 会生成 `specs/meta/index/traceability.md` 与 `specs/meta/index/traceability.json`。
- `generate-agent-dispatch` 会基于 `specs/meta/agents/agents.md` 的权威映射生成 `specs/meta/index/agent-dispatch.json`。
- `generate-tool-adapters` 会读取/初始化 `specs/meta/index/tool-adapters.json`，并自动生成各工具入口文件。
- `add-tool-adapter`/`remove-tool-adapter` 支持增减工具并自动维护共享入口文件引用计数。
- `resolve-agent-dispatch` 会按统一映射输出主责 Agent、建议 Skill、共享 Skill 仲裁提示，用于不同 AI 工具一致调度。
- `check-completeness` 会先刷新追溯矩阵，再检查 `REQ -> DSN -> TSK -> TEST` 链路完整性。
- `check-status` 除必需文件存在性外，还会检查主工件关键字段是否为非占位内容。
- `specs/meta/index/capability-matrix.md` 为人工维护项，更新后必须运行 `generate-index` 与 `check-completeness` 防止索引漂移。
- `check-drift` 仅检查 `src/` 下后缀为 `.ts/.js/.go/.py/.rs` 的代码文件，且必须包含标记串 `GENERATED FROM SPEC`。
- `check-code-quality` 阈值：单行 `>120` 为告警、`>200` 为错误，单文件 `>2000` 行为错误；`TODO/FIXME` 仅在注释上下文计数。
- `check-completeness` 规则：追溯矩阵为空（未发现 `req-*`）记为错误；`REQ` 缺失 `DSN/TSK/TEST` 记为错误，缺失 `ADR` 记为告警（用于渐进式补齐决策文档）。

## 例外处理
- 工具例外必须形成 ADR 与批准记录。
