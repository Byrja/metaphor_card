from typing import Optional

RED_FLAGS = {
    "suicide": ["хочу умереть", "покончить с собой", "суицид"],
    "self_harm": ["навредить себе", "самоповреждение"],
    "panic": ["паническая атака", "не могу дышать", "теряю контроль"],
    "violence": ["меня бьют", "мне угрожают", "насилие"],
}


def detect_red_flag(text: str) -> Optional[str]:
    lowered = text.lower()
    for category, triggers in RED_FLAGS.items():
        if any(trigger in lowered for trigger in triggers):
            return category
    return None


def safety_reply() -> str:
    return (
        "Спасибо, что поделился(ась). Похоже, тебе сейчас действительно тяжело.\n"
        "Я не могу заменить кризисную помощь, но важно, чтобы ты был(а) не один(одна).\n"
        "Пожалуйста, свяжись с близким человеком или экстренной службой в твоём регионе прямо сейчас."
    )
