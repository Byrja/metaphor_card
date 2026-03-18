from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class PatternScore:
    key: str
    score: float


THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "relationships": ("отнош", "партнер", "близ", "конфликт", "семья"),
    "work": ("работ", "проект", "карьер", "коллег", "выгоран"),
    "anxiety": ("трев", "страх", "паник", "неопредел", "напряж"),
    "self_worth": ("самооцен", "ценность", "стыд", "вина", "критик"),
    "money": ("деньг", "финанс", "доход", "долг", "бюджет"),
    "boundaries": ("границ", "отказ", "нет", "давлен", "личное пространство"),
}


def extract_theme_scores(texts: list[str]) -> list[PatternScore]:
    bag = " ".join(text.lower() for text in texts if text)
    counts: Counter[str] = Counter()

    for theme, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in bag:
                counts[theme] += 1

    total = sum(counts.values())
    if total == 0:
        return []

    ranked = [PatternScore(key=theme, score=round(value / total, 3)) for theme, value in counts.items()]
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
