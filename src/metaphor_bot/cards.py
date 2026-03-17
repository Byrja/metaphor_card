from dataclasses import dataclass
from random import choice, sample


@dataclass(frozen=True)
class Card:
    code: str
    title: str
    prompt: str


MVP_CARDS = [
    Card("mist_bridge", "Мост в тумане", "Где в твоей ситуации уже есть путь, который ты пока не называешь путём?"),
    Card("quiet_lamp", "Тихая лампа", "Что помогает тебе не гаснуть, даже если сейчас мало сил?"),
    Card("river_stone", "Камень у реки", "Что в тебе остаётся устойчивым, когда вокруг всё меняется?"),
    Card("inner_garden", "Внутренний сад", "Что в тебе просит бережного внимания и регулярной заботы?"),
    Card("open_window", "Открытое окно", "Какой новый взгляд на ситуацию уже доступен тебе сегодня?"),
]


def pick_day_card() -> Card:
    return choice(MVP_CARDS)


def pick_spread_cards(count: int) -> list[Card]:
    if count >= len(MVP_CARDS):
        return MVP_CARDS.copy()
    return sample(MVP_CARDS, k=count)
