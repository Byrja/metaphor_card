from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib
import json
import logging
import random


logger = logging.getLogger("metaphor_card.content")


def _load_yaml_module() -> object | None:
    try:
        return importlib.import_module("yaml")
    except ModuleNotFoundError:
        logger.warning("PyYAML is unavailable; using built-in content fallback")
        return None


FALLBACK_TAXONOMY = {
    "crisis_mode": {
        "avoid_intensity_gte": 4,
        "avoid_tags": ["panic", "despair"],
        "avoid_archetypes": ["abyss"],
    }
}
FALLBACK_DECK = {
    "deck": {"code": "base_mvp"},
    "cards": [
        {
            "code": "fallback_breath",
            "title": "Тихая пауза",
            "image_uri": "builtin://fallback/quiet_pause",
            "intensity_level": 1,
            "themes": ["pause", "support"],
            "archetypes": ["support"],
            "emotional_tags": ["calm"],
        },
        {
            "code": "fallback_focus",
            "title": "Луч света",
            "image_uri": "builtin://fallback/ray_of_light",
            "intensity_level": 2,
            "themes": ["clarity", "attention"],
            "archetypes": ["guide"],
            "emotional_tags": ["focus"],
        },
        {
            "code": "fallback_ground",
            "title": "Точка опоры",
            "image_uri": "builtin://fallback/anchor_point",
            "intensity_level": 2,
            "themes": ["grounding", "support"],
            "archetypes": ["anchor"],
            "emotional_tags": ["stable"],
        },
    ],
}
FALLBACK_LAYERS = {
    "l1_contact_with_card": ["Что в этой карте первым замечается тебе сейчас?"],
    "l2_link_to_self": ["На что это похоже в твоей текущей жизни?"],
    "l3_deepening": ["Что поможет пройти следующий шаг мягче и яснее?"],
    "l4_exit": ["Какой маленький шаг ты готов(а) сделать после этого?"],
}


@dataclass(frozen=True)
class Card:
    code: str
    title: str
    image_uri: str
    intensity_level: int
    themes: tuple[str, ...]
    archetypes: tuple[str, ...]
    emotional_tags: tuple[str, ...]


@dataclass(frozen=True)
class CrisisMode:
    avoid_intensity_gte: int
    avoid_tags: tuple[str, ...]
    avoid_archetypes: tuple[str, ...]


class ContentService:
    def __init__(self, root: str = "content") -> None:
        self.root = Path(root)
        self.decks: dict[str, list[Card]] = {}
        self.layers: dict[str, list[str]] = {}
        self.crisis_mode = CrisisMode(avoid_intensity_gte=4, avoid_tags=(), avoid_archetypes=())
        self.using_fallback = False
        self.approved_card_codes: tuple[str, ...] = ()
        self._load()

    def _read_yaml(self, path: Path, fallback_payload: dict, description: str) -> dict:
        yaml_module = _load_yaml_module()
        if yaml_module is None:
            self.using_fallback = True
            return fallback_payload

        try:
            return yaml_module.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("%s is unavailable at %s; using built-in fallback", description, path)
        except yaml_module.YAMLError as exc:
            logger.warning("%s at %s is invalid (%s); using built-in fallback", description, path, exc)
        self.using_fallback = True
        return fallback_payload


    def _manifest_path(self) -> Path:
        return self.root.parent / "assets" / "cards" / "style-c" / "approved_manifest.json"

    def _load_approved_card_codes(self) -> tuple[str, ...]:
        manifest_path = self._manifest_path()
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ()
        except json.JSONDecodeError as exc:
            logger.warning("Approved manifest at %s is invalid (%s); ignoring approved filter", manifest_path, exc)
            return ()

        raw_codes = payload.get("approved_cards", [])
        if not isinstance(raw_codes, list):
            logger.warning("Approved manifest at %s has non-list approved_cards; ignoring approved filter", manifest_path)
            return ()

        approved_codes = tuple(str(code).strip() for code in raw_codes if str(code).strip())
        if not approved_codes:
            return ()

        known_codes = {card.code for cards in self.decks.values() for card in cards}
        missing_codes = sorted(set(approved_codes) - known_codes)
        if missing_codes:
            logger.warning(
                "Approved manifest references unknown card codes %s; ignoring approved filter",
                ", ".join(missing_codes),
            )
            return ()

        return approved_codes

    def _apply_approved_filter(self) -> None:
        approved_codes = self._load_approved_card_codes()
        self.approved_card_codes = approved_codes
        if not approved_codes:
            return

        base_cards = self.decks.get("base_mvp", [])
        filtered = [card for card in base_cards if card.code in approved_codes]
        if not filtered:
            logger.warning("Approved manifest produced an empty base_mvp deck; using current deck fallback")
            return

        self.decks["base_mvp"] = filtered

    def _load(self) -> None:
        taxonomy_path = self.root / "card_taxonomy.yaml"
        taxonomy = self._read_yaml(taxonomy_path, FALLBACK_TAXONOMY, "Taxonomy")
        crisis = taxonomy.get("crisis_mode", {})
        self.crisis_mode = CrisisMode(
            avoid_intensity_gte=int(crisis.get("avoid_intensity_gte", 4)),
            avoid_tags=tuple(crisis.get("avoid_tags", [])),
            avoid_archetypes=tuple(crisis.get("avoid_archetypes", [])),
        )

        decks_dir = self.root / "decks"
        deck_files = sorted(decks_dir.glob("*.yaml"))
        if not deck_files:
            self.using_fallback = True
            deck_payloads = [FALLBACK_DECK]
        else:
            deck_payloads = [self._read_yaml(deck_file, FALLBACK_DECK, f"Deck '{deck_file.name}'") for deck_file in deck_files]

        for data in deck_payloads:
            deck = data.get("deck", {})
            deck_code = str(deck.get("code", "base_mvp"))
            cards = [
                Card(
                    code=item["code"],
                    title=item["title"],
                    image_uri=item.get("image_uri", ""),
                    intensity_level=int(item.get("intensity_level", 3)),
                    themes=tuple(item.get("themes", [])),
                    archetypes=tuple(item.get("archetypes", [])),
                    emotional_tags=tuple(item.get("emotional_tags", [])),
                )
                for item in data.get("cards", [])
                if item.get("code") and item.get("title")
            ]
            if cards:
                self.decks[deck_code] = cards

        if "base_mvp" not in self.decks:
            self.using_fallback = True
            self.decks["base_mvp"] = self._cards_from_payload(FALLBACK_DECK)

        self._apply_approved_filter()

        layers_path = self.root / "prompts" / "layers.yaml"
        layer_data = self._read_yaml(layers_path, FALLBACK_LAYERS, "Prompt layers")
        self.layers = {
            "l1": list(layer_data.get("l1_contact_with_card", FALLBACK_LAYERS["l1_contact_with_card"])),
            "l2": list(layer_data.get("l2_link_to_self", FALLBACK_LAYERS["l2_link_to_self"])),
            "l3": list(layer_data.get("l3_deepening", FALLBACK_LAYERS["l3_deepening"])),
            "l4": list(layer_data.get("l4_exit", FALLBACK_LAYERS["l4_exit"])),
        }

    def _cards_from_payload(self, payload: dict) -> list[Card]:
        return [
            Card(
                code=item["code"],
                title=item["title"],
                image_uri=item.get("image_uri", ""),
                intensity_level=int(item.get("intensity_level", 3)),
                themes=tuple(item.get("themes", [])),
                archetypes=tuple(item.get("archetypes", [])),
                emotional_tags=tuple(item.get("emotional_tags", [])),
            )
            for item in payload.get("cards", [])
        ]

    def _filter_cards(self, cards: list[Card], safety_mode: str) -> list[Card]:
        if safety_mode != "conservative":
            return cards

        filtered: list[Card] = []
        for card in cards:
            if card.intensity_level >= self.crisis_mode.avoid_intensity_gte:
                continue
            if any(tag in self.crisis_mode.avoid_tags for tag in card.emotional_tags):
                continue
            if any(arc in self.crisis_mode.avoid_archetypes for arc in card.archetypes):
                continue
            filtered.append(card)
        return filtered

    def random_day_card(self, safety_mode: str = "normal") -> Card:
        base = self._filter_cards(self.decks.get("base_mvp", []), safety_mode)
        if not base:
            raise RuntimeError("No cards available for selected safety mode")
        return random.choice(base)

    def random_situation_cards(self, safety_mode: str = "normal") -> list[Card]:
        base = self._filter_cards(self.decks.get("base_mvp", []), safety_mode)
        if len(base) < 3:
            raise RuntimeError("Not enough cards for 3-card spread in selected safety mode")
        return random.sample(base, k=3)

    def random_prompt(self, layer: str) -> str:
        options = self.layers.get(layer, [])
        if not options:
            raise RuntimeError(f"Prompt layer '{layer}' is empty")
        return random.choice(options)

    def checkin_prompts(self) -> list[str]:
        return [
            self.random_prompt("l1"),
            self.random_prompt("l2"),
            self.random_prompt("l4"),
        ]
