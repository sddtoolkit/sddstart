"""Tests for CLI arguments and path security."""

from __future__ import annotations

import argparse
import sys
import unittest
from unittest import mock
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd import cli  # noqa: E402
from sdd.handlers import commands as command_handlers  # noqa: E402


class CliValidationTests(unittest.TestCase):
    """Covers argument validation and path traversal protection."""

    def test_validating_slug_value(self) -> None:
        self.assertEqual(cli.validate_slug("Auth Module"), "auth-module")
        self.assertIsNone(cli.validate_slug("!!!"))

    def test_resolve_safe_path(self) -> None:
        inside_path = cli.resolve_safe_path("govs/G01-governance-and-process.md")
        assert inside_path is not None
        self.assertTrue(inside_path.is_absolute())

        outside_path = cli.resolve_safe_path("../outside.md")
        self.assertIsNone(outside_path)

        absolute_path = cli.resolve_safe_path("/tmp/outside.md")
        self.assertIsNone(absolute_path)

        empty_path = cli.resolve_safe_path(None)
        self.assertIsNone(empty_path)

    def test_validating_semver(self) -> None:
        self.assertTrue(cli.validate_semver("1.2.3"))
        self.assertFalse(cli.validate_semver("1.2"))

    def test_command_verb_form_only(self) -> None:
        parser = cli.build_parser()

        args = parser.parse_args(["create-requirement", "auth"])
        self.assertTrue(hasattr(args, "running"))

        with self.assertRaises(SystemExit):
            parser.parse_args(["creating-requirement", "auth"])

    def test_resolve_agent_dispatch_flags(self) -> None:
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "resolve-agent-dispatch",
                "--task",
                "complete release gates",
                "--stage",
                "release",
                "--skills",
                "generate-changelog-release-skill,maintain-runbook-skill",
                "--json",
            ]
        )
        self.assertTrue(hasattr(args, "running"))
        self.assertTrue(args.as_json)

    def test_add_tool_adapter_flags(self) -> None:
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "add-tool-adapter",
                "opencode",
                "OpenCode",
                "--entry-file",
                "OPENCODE.md",
                "--entry-format",
                "markdown",
                "--shared-entry",
                "--extra-entry",
                ".opencode/init:text",
            ]
        )
        self.assertTrue(hasattr(args, "running"))
        self.assertTrue(args.shared_entry)

    def test_create_design_named_file_uses_ccc_prefix(self) -> None:
        args = argparse.Namespace(slug="api-gateway", ccc="201", nn=None)
        with (
            mock.patch.object(command_handlers, "copy_template", return_value=True) as copy_template,
            mock.patch.object(command_handlers, "refresh_index_after_change", return_value=0),
            mock.patch.object(command_handlers, "get_next_nn", return_value="01"),
        ):
            result = command_handlers.create_design(args)

        self.assertEqual(result, 0)
        self.assertEqual(copy_template.call_args.args[0], "templates/design.template.md")
        self.assertRegex(copy_template.call_args.args[1], r"^2-designs/DS-20101-api-gateway-design\.md$")


if __name__ == "__main__":
    unittest.main()
