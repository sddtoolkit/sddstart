# 测试用例：基线治理校验

## 元信息
- 用例编号：test-baseline-001
- 版本：v1.0
- 负责人：tester-agent
- 日期：2026-03-02

## 目标
- 目标：验证主工件非占位校验和追踪实体存在性校验已生效。

## 前置条件
- 前置条件：核心文档已回填有效内容；新增 ADR/任务工件已创建。

## 步骤
1. 执行 `python3 specs/meta/tools/sddtool.py check-status`。
2. 执行 `python3 specs/meta/tools/sddtool.py check-completeness`。
3. 执行 `python3 specs/meta/tools/sddtool.py validate-requirement` 与 `validate-design`。

## 期望结果
- 期望结果：所有命令返回成功；若将关键字段改为空则命令返回失败。

## 数据与环境
- 测试数据：`req-baseline-001`、`dsn-baseline-architecture`、`tsk-baseline-001`、`adr-20260302-baseline-governance`。
- 环境：Python 3.10+，Linux 或 macOS。

## 优先级与类型
- 优先级：P0
- 类型：集成/回归

## 追踪
- 关联需求：req-baseline-001
- 关联任务：tsk-baseline-001
