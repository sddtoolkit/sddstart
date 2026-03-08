"""req/design validator 行为测试。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.validators.designvalidator import check_design_file  # noqa: E402
from sdd.validators.reqvalidator import check_requirement_file  # noqa: E402


class ValidatorsTests(unittest.TestCase):
    """覆盖需求与设计文档章节校验。"""

    def test_requirement_validator_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            req_path = Path(tmp_dir) / "requirements.md"
            req_path.write_text(
                "\n".join(
                    [
                        "# 需求说明",
                        "## 元信息",
                        "- 文档编号：req-baseline-001",
                        "- 版本：v1.0",
                        "- 负责人：specifier-agent",
                        "- 日期：2026-03-02",
                        "## 目标与范围",
                        "- 目标：定义模板工程能力边界",
                        "- 范围：spec 与工具链",
                        "## 功能需求",
                        "- FR-1：应支持完整追踪链路",
                        "## 验收标准",
                        "- AC-1：追踪矩阵包含 req/design/task/test",
                        "## 追踪",
                        "- 关联设计：dsn-baseline-architecture",
                        "- 关联任务：tsk-baseline-001",
                        "- 关联测试：test-baseline-001",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_requirement_file(req_path), 0)

            req_path.write_text(
                "# 需求说明\n## 元信息\n- 文档编号：req-baseline-001\n- 版本：\n## 目标与范围\n## 功能需求\n## 验收标准\n## 追踪\n",
                encoding="utf-8",
            )
            self.assertEqual(check_requirement_file(req_path), 1)

    def test_design_validator_pass_with_alternative_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            design_path = Path(tmp_dir) / "architecture.md"
            design_path.write_text(
                "\n".join(
                    [
                        "# 架构设计",
                        "## 元信息",
                        "- 文档编号：dsn-baseline-architecture",
                        "- 版本：v1.0",
                        "- 负责人：architect-agent",
                        "- 日期：2026-03-02",
                        "## 安全与隐私",
                        "- 认证与授权：使用仓库权限最小化策略",
                        "- 数据保护：所有文档 UTF-8 编码",
                        "## 可靠性与性能",
                        "- 容量与性能目标：校验命令 5 秒内完成",
                        "## 追踪",
                        "- 关联需求：req-baseline-001",
                        "- 关联任务：tsk-baseline-001",
                        "## 系统边界",
                        "- 边界定义：仅处理 specs 目录",
                        "- 外部依赖：Python 标准库",
                        "## 接口与契约",
                        "- 对外接口：python3 specs/meta/tools/sddtool.py <subcommand>",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_design_file(design_path), 0)

    def test_design_validator_fail_without_alternative_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            design_path = Path(tmp_dir) / "architecture.md"
            design_path.write_text(
                "\n".join(
                    [
                        "# 架构设计",
                        "## 元信息",
                        "## 安全与隐私",
                        "## 可靠性与性能",
                        "## 追踪",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(check_design_file(design_path), 1)


if __name__ == "__main__":
    unittest.main()
