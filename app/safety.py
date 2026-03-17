from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyDecision:
    risk_level: str
    requires_escalation: bool
    matched_markers: tuple[str, ...]


HIGH_RISK_MARKERS = (
    "суицид",
    "поконч",
    "убить себя",
    "самоповреж",
    "не хочу жить",
    "вскрыть",
)

MEDIUM_RISK_MARKERS = (
    "паника",
    "не справляюсь",
    "очень страшно",
    "хочу исчезнуть",
    "боюсь сорваться",
)

CRISIS_REPLY = (
    "Мне очень жаль, что тебе сейчас так тяжело. Ты не обязан(а) оставаться с этим в одиночку.\n"
    "Сейчас важнее всего твоя безопасность. Если есть риск причинить себе вред, пожалуйста, немедленно "
    "обратись в экстренные службы твоей страны или к близкому человеку, которому доверяешь.\n"
    "Если хочешь, я помогу сделать первый шаг: написать одному человеку и попросить побыть рядом."
)

MEDIUM_RISK_REPLY = (
    "Похоже, сейчас очень непросто. Давай без углубления в карты.\n"
    "Сделай короткое заземление: оглянись вокруг и назови 5 предметов, которые видишь.\n"
    "Если состояние не отпускает, лучше связаться с живым специалистом или близким человеком прямо сейчас."
)


def assess_text_risk(text: str) -> SafetyDecision:
    normalized = text.lower()

    matched_high = tuple(marker for marker in HIGH_RISK_MARKERS if marker in normalized)
    if matched_high:
        return SafetyDecision(
            risk_level="high",
            requires_escalation=True,
            matched_markers=matched_high,
        )

    matched_medium = tuple(marker for marker in MEDIUM_RISK_MARKERS if marker in normalized)
    if matched_medium:
        return SafetyDecision(
            risk_level="medium",
            requires_escalation=True,
            matched_markers=matched_medium,
        )

    return SafetyDecision(
        risk_level="low",
        requires_escalation=False,
        matched_markers=(),
    )
