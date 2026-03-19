import tempfile
import unittest
from pathlib import Path

from scripts import ux_integrator


class UxIntegratorTests(unittest.TestCase):
    def _create_pack(
        self,
        root: Path,
        *,
        map_text: str | None = None,
        extra_files: dict[str, str] | None = None,
    ) -> Path:
        pack_root = root / "docs" / "ux-pack-v3-python"
        (pack_root / "docs").mkdir(parents=True)
        if map_text is not None:
            (pack_root / "docs" / "UX_PATCH_MAP_PYTHON.md").write_text(map_text, encoding="utf-8")
        for relative_path, content in (extra_files or {}).items():
            path = pack_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return pack_root

    def test_validate_pack_requires_python_patch_map(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_root = self._create_pack(
                Path(tmpdir),
                map_text=None,
                extra_files={"docs/UX_CHANGELOG_v3.md": "# changelog\n"},
            )

            with self.assertRaisesRegex(ux_integrator.IntegrationValidationError, "python-real-path-map required"):
                ux_integrator.validate_pack(pack_root)

    def test_validate_pack_requires_real_app_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_root = self._create_pack(
                Path(tmpdir),
                map_text="# map\n- docs/DEPLOY_RUNBOOK.md\n",
                extra_files={"docs/UX_CHANGELOG_v3.md": "# changelog\n"},
            )

            with self.assertRaisesRegex(ux_integrator.IntegrationValidationError, r"real app/\* paths"):
                ux_integrator.validate_pack(pack_root)

    def test_validate_pack_rejects_forbidden_targets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_root = self._create_pack(
                Path(tmpdir),
                map_text="# map\n- app/bot.py\n",
                extra_files={"app/ux_copy.py": "print('forbidden')\n"},
            )

            with self.assertRaisesRegex(ux_integrator.IntegrationValidationError, "forbidden targets"):
                ux_integrator.validate_pack(pack_root)

    def test_apply_pack_dry_run_keeps_repository_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_root = self._create_pack(
                Path(tmpdir),
                map_text="# map\n- app/bot.py\n- app/content.py\n",
                extra_files={
                    "docs/UX_CHANGELOG_v3.md": "# changelog\n",
                    "content/prompts/python_map_notice.yaml": "notes:\n  - keep app paths real\n",
                },
            )

            result = ux_integrator.apply_pack(pack_root, dry_run=True)

            targets = {copy.target.relative_to(ux_integrator.REPO_ROOT).as_posix() for copy in result.planned_copies}
            self.assertIn("docs/UX_PATCH_MAP_PYTHON.md", targets)
            self.assertIn("content/prompts/python_map_notice.yaml", targets)
            self.assertFalse((ux_integrator.REPO_ROOT / "content/prompts/python_map_notice.yaml").exists())

    def test_apply_pack_copies_allowed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            pack_root = self._create_pack(
                temp_root,
                map_text="# map\n- app/bot.py\n- app/content.py\n",
                extra_files={"docs/UX_CHANGELOG_v3.md": "# changelog\n"},
            )
            repo_root = temp_root / "repo"
            repo_root.mkdir()

            original_repo_root = ux_integrator.REPO_ROOT
            ux_integrator.REPO_ROOT = repo_root
            try:
                result = ux_integrator.apply_pack(pack_root, dry_run=False)
            finally:
                ux_integrator.REPO_ROOT = original_repo_root

            self.assertEqual(len(result.planned_copies), 2)
            self.assertTrue((repo_root / "docs/UX_PATCH_MAP_PYTHON.md").exists())
            self.assertEqual((repo_root / "docs/UX_CHANGELOG_v3.md").read_text(encoding="utf-8"), "# changelog\n")


if __name__ == "__main__":
    unittest.main()
