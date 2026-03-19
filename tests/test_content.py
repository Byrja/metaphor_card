import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        if "l1_contact_with_card:" in text:
            return {
                "l1_contact_with_card": ["Что замечается?"],
                "l2_link_to_self": ["На что это похоже?"],
                "l3_deepening": ["Что поможет?"],
                "l4_exit": ["Какой шаг?"],
            }
        raise FakeYaml.YAMLError("unsupported fixture")


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


class ContentApprovedCardsTests(unittest.TestCase):
    def _write_fixture_content(self, root: Path) -> Path:
        content_root = root / "content"
        (content_root / "decks").mkdir(parents=True)
        (content_root / "prompts").mkdir(parents=True)
        (root / "assets" / "cards" / "style-c").mkdir(parents=True)

        (content_root / "card_taxonomy.yaml").write_text(
            "crisis_mode:\n  avoid_intensity_gte: 4\n  avoid_tags: []\n  avoid_archetypes: []\n",
            encoding="utf-8",
        )
        (content_root / "decks" / "base.yaml").write_text(
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
        (content_root / "prompts" / "layers.yaml").write_text(
            """
            l1_contact_with_card: ["Что замечается?"]
            l2_link_to_self: ["На что это похоже?"]
            l3_deepening: ["Что поможет?"]
            l4_exit: ["Какой шаг?"]
            """,
            encoding="utf-8",
        )
        return content_root

    def test_runtime_uses_only_approved_cards_when_manifest_is_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_root = self._write_fixture_content(root)
            (root / "assets" / "cards" / "style-c" / "approved_manifest.json").write_text(
                json.dumps({"approved_cards": ["c2", "c3"]}, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch("app.content._load_yaml_module", return_value=FakeYaml):
                service = ContentService(content_root.as_posix())

        self.assertEqual([card.code for card in service.decks["base_mvp"]], ["c2", "c3"])

    def test_invalid_approved_manifest_falls_back_to_current_deck(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_root = self._write_fixture_content(root)
            (root / "assets" / "cards" / "style-c" / "approved_manifest.json").write_text(
                json.dumps({"approved_cards": ["missing-code"]}, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch("app.content._load_yaml_module", return_value=FakeYaml):
                service = ContentService(content_root.as_posix())

        self.assertEqual(len(service.decks["base_mvp"]), 3)


if __name__ == "__main__":
    unittest.main()
