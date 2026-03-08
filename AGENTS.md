# AGENTS.md

本入口文件服务工具：Codex、Kimi Code、Kiro、OpenCode

## 统一约束
- Agent 权威映射：`specs/meta/agents/agents.md`
- Skill 权威清单：`specs/meta/skills/skills.md`
- 调度契约：`specs/meta/index/agent-dispatch.json`
- 工具清单与格式：`specs/meta/index/tool-adapters.json`

## 执行顺序
1. `python3 specs/meta/tools/sddtool.py generate-agent-dispatch`
2. `python3 specs/meta/tools/sddtool.py resolve-agent-dispatch --task "<任务描述>" --json`
3. 按输出的 `primary_agent` 与 `recommended_skills` 执行。

## 常用命令
- `python3 specs/meta/tools/sddtool.py initialize`
- `python3 specs/meta/tools/sddtool.py generate-index`
- `python3 specs/meta/tools/sddtool.py generate-traceability-matrix`
- `python3 specs/meta/tools/sddtool.py check-status`
- `python3 specs/meta/tools/sddtool.py check-governance`
- `python3 specs/meta/tools/sddtool.py check-completeness`
- `python3 specs/meta/tools/sddtool.py check-naming`
- `python3 specs/meta/tools/sddtool.py check-drift`

_该文件由 `generate-tool-adapters` 自动生成。_
