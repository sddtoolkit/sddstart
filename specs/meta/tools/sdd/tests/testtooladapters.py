"""Tests for multi-tool adapter manifest management."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from sdd.generators.tooladaptergenerator import (  # noqa: E402
    add_tool_adapter,
    build_default_tool_adapter_manifest,
    remove_tool_adapter,
    sync_tool_adapter_entries,
)


class ToolAdapterTests(unittest.TestCase):
    """Covers tool addition/removal and shared entry reclamation."""

    def test_remove_last_tool_reclaims_shared_entry(self) -> None:
        manifest = build_default_tool_adapter_manifest()

        manifest, deleted_paths = remove_tool_adapter(manifest, "kiro")
        self.assertEqual(deleted_paths, [])

        manifest, deleted_paths = remove_tool_adapter(manifest, "codex")
        self.assertEqual(deleted_paths, [])

        manifest, deleted_paths = remove_tool_adapter(manifest, "kimi-code")
        self.assertEqual(deleted_paths, [])

        manifest, deleted_paths = remove_tool_adapter(manifest, "opencode")
        self.assertIn("AGENTS.md", deleted_paths)

    def test_add_tool_to_shared_entry(self) -> None:
        manifest = build_default_tool_adapter_manifest()
        manifest = add_tool_adapter(
            manifest=manifest,
            tool_id="newcode",
            display_name="NewCode",
            entry_file="AGENTS.md",
            entry_format="markdown",
            shared_entry=True,
        )

        newcode = next(item for item in manifest["tools"] if item["tool_id"] == "newcode")
        self.assertTrue(newcode["entry_ids"])

        shared_entry = next(item for item in manifest["entries"] if item["path"] == "AGENTS.md")
        self.assertIn("newcode", shared_entry["tools"])

    def test_sync_entries_writes_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest = build_default_tool_adapter_manifest()
            written = sync_tool_adapter_entries(repo_root, manifest)

            self.assertIn("AGENTS.md", written)
            self.assertTrue((repo_root / "AGENTS.md").exists())
            self.assertTrue((repo_root / ".crush/init").exists())


if __name__ == "__main__":
    unittest.main()
