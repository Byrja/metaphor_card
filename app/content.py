from dataclasses import dataclass
from pathlib import Path
import random

import yaml


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
        self._load()

    def _load(self) -> None:
        taxonomy_path = self.root / "card_taxonomy.yaml"
        taxonomy = yaml.safe_load(taxonomy_path.read_text())
        crisis = taxonomy.get("crisis_mode", {})
        self.crisis_mode = CrisisMode(
            avoid_intensity_gte=int(crisis.get("avoid_intensity_gte", 4)),
            avoid_tags=tuple(crisis.get("avoid_tags", [])),
            avoid_archetypes=tuple(crisis.get("avoid_archetypes", [])),
        )

        decks_dir = self.root / "decks"
        for deck_file in decks_dir.glob("*.yaml"):
            data = yaml.safe_load(deck_file.read_text())
            deck_code = data["deck"]["code"]
            cards = [
                Card(
                    code=item["code"],
                    title=item["title"],
                    image_uri=item["image_uri"],
                    intensity_level=int(item.get("intensity_level", 3)),
                    themes=tuple(item.get("themes", [])),
                    archetypes=tuple(item.get("archetypes", [])),
                    emotional_tags=tuple(item.get("emotional_tags", [])),
                )
                for item in data.get("cards", [])
            ]
            self.decks[deck_code] = cards

        layers_path = self.root / "prompts" / "layers.yaml"
        layer_data = yaml.safe_load(layers_path.read_text())
        self.layers = {
            "l1": layer_data.get("l1_contact_with_card", []),
            "l2": layer_data.get("l2_link_to_self", []),
            "l3": layer_data.get("l3_deepening", []),
            "l4": layer_data.get("l4_exit", []),
        }

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
