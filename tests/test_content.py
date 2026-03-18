import tempfile
import unittest
from pathlib import Path
import struct
from unittest.mock import patch
import zlib

from app.content import ContentService


class FakeYaml:
    class YAMLError(Exception):
        pass

    @staticmethod
    def safe_load(text: str):
        if "crisis_mode:" in text:
            return {
                "crisis_mode": {
                    "avoid_intensity_gte": 4,
                    "avoid_tags": [],
                    "avoid_archetypes": [],
                }
            }
        if "deck:" in text:
            return {
                "deck": {"code": "base_mvp"},
                "cards": [
                    {"code": "c1", "title": "Первая карта", "image_uri": "local://1"},
                    {"code": "c2", "title": "Вторая карта", "image_uri": "local://2"},
                    {"code": "c3", "title": "Третья карта", "image_uri": "local://3"},
                ],
            }
        raise FakeYaml.YAMLError("unsupported fixture")


def _write_png(path: Path, width: int, height: int) -> None:
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + b"\x80\x40\x20" * width for _ in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(raw))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


class ContentFallbackTests(unittest.TestCase):
    def test_missing_content_directory_uses_builtin_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = ContentService(Path(tmp, "missing").as_posix())

        self.assertTrue(service.using_fallback)
        self.assertEqual(len(service.decks["base_mvp"]), 3)
        self.assertEqual(len(service.random_situation_cards()), 3)
        self.assertTrue(service.random_prompt("l1"))

    def test_missing_prompt_file_only_falls_back_for_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decks").mkdir(parents=True)
            (root / "card_taxonomy.yaml").write_text(
                "crisis_mode:\n  avoid_intensity_gte: 4\n  avoid_tags: []\n  avoid_archetypes: []\n",
                encoding="utf-8",
            )
            (root / "decks" / "base.yaml").write_text(
                """
                deck:
                  code: base_mvp
                cards:
                  - code: c1
                    title: Первая карта
                    image_uri: local://1
                  - code: c2
                    title: Вторая карта
                    image_uri: local://2
                  - code: c3
                    title: Третья карта
                    image_uri: local://3
                """,
                encoding="utf-8",
            )
            with patch("app.content._load_yaml_module", return_value=FakeYaml):
                service = ContentService(root.as_posix())

        self.assertTrue(service.using_fallback)
        self.assertIn(service.random_day_card().title, {"Первая карта", "Вторая карта", "Третья карта"})
        self.assertTrue(service.random_prompt("l4"))

    def test_manifest_overrides_image_uri_for_approved_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_root = root / "content"
            assets_root = root / "assets" / "cards" / "style-c" / "drafts"
            (content_root / "decks").mkdir(parents=True)
            assets_root.mkdir(parents=True)
            (content_root / "card_taxonomy.yaml").write_text(
                "crisis_mode:\n  avoid_intensity_gte: 4\n  avoid_tags: []\n  avoid_archetypes: []\n",
                encoding="utf-8",
            )
            (content_root / "decks" / "base.yaml").write_text(
                """
                deck:
                  code: base_mvp
                cards:
                  - code: misty_lake
                    title: Первая карта
                    image_uri: local://1
                  - code: c2
                    title: Вторая карта
                    image_uri: local://2
                  - code: c3
                    title: Третья карта
                    image_uri: local://3
                """,
                encoding="utf-8",
            )
            (content_root / "prompts").mkdir(parents=True)
            (content_root / "prompts" / "layers.yaml").write_text(
                """
                l1_contact_with_card: [\"Вопрос 1\"]
                l2_link_to_self: [\"Вопрос 2\"]
                l3_deepening: [\"Вопрос 3\"]
                l4_exit: [\"Вопрос 4\"]
                """,
                encoding="utf-8",
            )
            (root / "assets" / "cards" / "style-c" / "manifest.yaml").write_text(
                """
                version: 1
                cards:
                  - id: style_c_001
                    slug: misty_lake
                    title_ru: \"Туманное озеро\"
                    tags: [style-c, approved]
                    source_file: drafts/source.png
                    processed_file: processed/misty_lake.webp
                    status: approved
                """,
                encoding="utf-8",
            )
            _write_png(assets_root / "source.png", 300, 400)

            service = ContentService(content_root.as_posix())

        cards = {card.code: card for card in service.decks["base_mvp"]}
        self.assertEqual(cards["misty_lake"].image_uri, "processed/misty_lake.webp")
        self.assertEqual(cards["c2"].image_uri, "local://2")


if __name__ == "__main__":
    unittest.main()
