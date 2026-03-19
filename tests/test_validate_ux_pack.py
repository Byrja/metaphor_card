import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ux_pack import ValidationError, validate_pack


class ValidateUxPackTests(unittest.TestCase):
    def _write_manifest(self, root: Path, entry: dict[str, str]) -> None:
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "allowed_destination_prefixes": ["content/", "docs/"],
                    "forbidden_destination_prefixes": ["app/", "src/", "scripts/", "tests/"],
                    "forbidden_extensions": [".py", ".sh"],
                    "files": [entry],
                }
            ),
            encoding="utf-8",
        )

    def test_validate_pack_accepts_yaml_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            approved = root / "approved"
            approved.mkdir()
            yaml_path = approved / "layers.yaml"
            yaml_path.write_text("items:\n  - safe copy\n", encoding="utf-8")
            json_path = approved / "safety.json"
            json_path.write_text('{"message": "ok"}\n', encoding="utf-8")
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "allowed_destination_prefixes": ["content/", "docs/"],
                        "forbidden_destination_prefixes": ["app/", "src/", "scripts/", "tests/"],
                        "forbidden_extensions": [".py", ".sh"],
                        "files": [
                            {
                                "source": "approved/layers.yaml",
                                "destination": "content/prompts/layers.yaml",
                                "format": "yaml",
                            },
                            {
                                "source": "approved/safety.json",
                                "destination": "docs/ux-pack-v3-python/safety_replies.json",
                                "format": "json",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            validated = validate_pack(root)

        self.assertEqual(validated, ["approved/layers.yaml", "approved/safety.json"])

    def test_validate_pack_rejects_placeholder_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            approved = root / "approved"
            approved.mkdir()
            broken = approved / "layers.yaml"
            broken.write_text("items:\n  - TODO replace\n", encoding="utf-8")
            self._write_manifest(
                root,
                {
                    "source": "approved/layers.yaml",
                    "destination": "content/prompts/layers.yaml",
                    "format": "yaml",
                },
            )

            with self.assertRaises(ValidationError):
                validate_pack(root)

    def test_validate_pack_rejects_runtime_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            approved = root / "approved"
            approved.mkdir()
            source = approved / "copy.yaml"
            source.write_text("items:\n  - ok\n", encoding="utf-8")
            self._write_manifest(
                root,
                {
                    "source": "approved/copy.yaml",
                    "destination": "app/ux_copy.py",
                    "format": "yaml",
                },
            )

            with self.assertRaises(ValidationError):
                validate_pack(root)


if __name__ == "__main__":
    unittest.main()
