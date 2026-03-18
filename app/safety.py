from dataclasses import dataclass

from app.ux_copy import CRISIS_REPLY, MEDIUM_RISK_REPLY


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
