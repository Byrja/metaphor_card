import json
import tempfile
import unittest
from pathlib import Path

from scripts import apply_ux_patch_map


class ApplyUxPatchMapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "docs").mkdir(parents=True)
        (self.root / "reports").mkdir(parents=True)
        self.original_repo_root = apply_ux_patch_map.repo_root
        apply_ux_patch_map.repo_root = lambda: self.root

    def tearDown(self):
        apply_ux_patch_map.repo_root = self.original_repo_root
        self.temp_dir.cleanup()

    def write_target(self, relative_path: str, text: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_map(self, items):
        path = self.root / "docs/UX_PATCH_MAP_PYTHON_v2.json"
        path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_report(self):
        return json.loads((self.root / "reports/ux_patch_apply_report.json").read_text(encoding="utf-8"))

    def test_apply_success_updates_target_and_writes_report(self):
        self.write_target("app/sample.py", "print('old')\n")
        self.write_map(
            [
                {
                    "target_file": "app/sample.py",
                    "target_symbol": "demo",
                    "old_snippet": "print('old')",
                    "new_snippet": "print('new')",
                    "source_key": "sample-1",
                }
            ]
        )

        result = apply_ux_patch_map.run("docs/UX_PATCH_MAP_PYTHON_v2.json", "apply")

        self.assertTrue(result.ok)
        self.assertIn("print('new')", (self.root / "app/sample.py").read_text(encoding="utf-8"))
        report = self.read_report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["applied"], 1)
        self.assertEqual(report["items"][0]["status"], "applied")

    def test_not_found_fails_and_still_writes_report(self):
        self.write_target("app/sample.py", "print('old')\n")
        self.write_map(
            [
                {
                    "target_file": "app/sample.py",
                    "old_snippet": "print('missing')",
                    "new_snippet": "print('new')",
                    "source_key": "sample-2",
                }
            ]
        )

        result = apply_ux_patch_map.run("docs/UX_PATCH_MAP_PYTHON_v2.json", "dry-run")

        self.assertFalse(result.ok)
        self.assertIn("not found", result.errors[0])
        report = self.read_report()
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["errors"], 1)

    def test_duplicate_match_fails_without_silent_replace(self):
        self.write_target("app/sample.py", "old\nold\n")
        self.write_map(
            [
                {
                    "target_file": "app/sample.py",
                    "old_snippet": "old",
                    "new_snippet": "new",
                    "source_key": "sample-3",
                }
            ]
        )

        result = apply_ux_patch_map.run("docs/UX_PATCH_MAP_PYTHON_v2.json", "apply")

        self.assertFalse(result.ok)
        self.assertIn("ambiguous", result.errors[0])
        self.assertEqual((self.root / "app/sample.py").read_text(encoding="utf-8"), "old\nold\n")
        report = self.read_report()
        self.assertEqual(report["items"][0]["occurrences"], 2)

    def test_noop_patch_is_rejected(self):
        self.write_target("app/sample.py", "same\n")
        self.write_map(
            [
                {
                    "target_file": "app/sample.py",
                    "old_snippet": "same",
                    "new_snippet": "same",
                    "source_key": "sample-4",
                }
            ]
        )

        result = apply_ux_patch_map.run("docs/UX_PATCH_MAP_PYTHON_v2.json", "dry-run")

        self.assertFalse(result.ok)
        self.assertIn("No-op", result.errors[0])
        report = self.read_report()
        self.assertEqual(report["items"][0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
