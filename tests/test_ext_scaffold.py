#!/usr/bin/env python3
"""Developer scaffold tests (Initiative 11, Epic 4)."""

import tempfile
import unittest
from pathlib import Path

from initiatives.i11.policy_kit.checks import run_policy_suite
from initiatives.i11.scaffold.template import scaffold_extension

EXPECTED_FILES = {
    "manifest.json", "extension.py", "docs/README.md", "web_card.html",
    "wizard_step.py", "cli_snippet.py", "mcp_snippet.py", "RETRO.md",
}


class TestScaffold(unittest.TestCase):
    def test_scaffold_generates_all_surfaces(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-scaffold-"))
        result = scaffold_extension(
            "Demo Ext", description="demo", author="tester", out_dir=tmp,
            data_scopes=["jobs:read"], action_kinds=["read", "draft"])
        for expected in EXPECTED_FILES:
            self.assertIn(expected, result["files"], expected)
        out = Path(result["dir"])
        self.assertTrue((out / "manifest.json").is_file())
        self.assertTrue((out / "tests" / "test_demo_ext.py").is_file())

    def test_scaffolded_manifest_validates(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-scaffold-"))
        result = scaffold_extension("Demo Ext 2", out_dir=tmp)
        from initiatives.i11.manifest.schema import load_manifest
        manifest = load_manifest(result["dir"])
        self.assertEqual(manifest["id"], "demo-ext-2")

    def test_scaffolded_extension_passes_policy_suite(self):
        # A freshly scaffolded extension (with implemented stubs replaced by
        # no-ops) must pass the policy kit: the template is safe by default.
        tmp = Path(tempfile.mkdtemp(prefix="veto-scaffold-"))
        result = scaffold_extension("Safe Default", out_dir=tmp,
                                    action_kinds=["read"])
        ext_py = Path(result["dir"]) / "extension.py"
        content = ext_py.read_text()
        content = content.replace(
            'raise NotImplementedError(', '# raise NotImplementedError(')
        content = content.replace(
            '    # raise NotImplementedError(',
            "    return {'ok': True}  # scaffold default\n"
            "    # raise NotImplementedError(")
        ext_py.write_text(content)
        report = run_policy_suite(result["dir"])
        failures = [r for r in report["results"] if not r["passed"]]
        self.assertEqual(failures, [], f"policy failures: {failures}")

    def test_bad_name_rejected(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-scaffold-"))
        with self.assertRaises(ValueError):
            scaffold_extension("!!!", out_dir=tmp)


if __name__ == "__main__":
    unittest.main()
