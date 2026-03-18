from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib
import logging
import random

from app.cards_manifest import approved_manifest_map

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
        self.manifest_cards: dict[str, str] = {}
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

    def _load(self) -> None:
        self.manifest_cards = self._load_manifest_cards()
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
                    image_uri=self._resolve_image_uri(str(item["code"]), item.get("image_uri", "")),
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
                image_uri=self._resolve_image_uri(str(item["code"]), item.get("image_uri", "")),
                intensity_level=int(item.get("intensity_level", 3)),
                themes=tuple(item.get("themes", [])),
                archetypes=tuple(item.get("archetypes", [])),
                emotional_tags=tuple(item.get("emotional_tags", [])),
            )
            for item in payload.get("cards", [])
        ]

    def _load_manifest_cards(self) -> dict[str, str]:
        manifest_path = self.root.parent / "assets" / "cards" / "style-c" / "manifest.yaml"
        approved_cards = approved_manifest_map(manifest_path)
        return {slug: entry.processed_file for slug, entry in approved_cards.items()}

    def _resolve_image_uri(self, code: str, existing: str) -> str:
        return self.manifest_cards.get(code, existing)

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
