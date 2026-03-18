from metaphor_bot.cards import pick_day_card, pick_spread_cards


CHECK_IN_STEPS = [
    "Что ты сейчас чувствуешь (1-3 слова)?",
    "Что в этом чувстве для тебя самое важное прямо сейчас?",
    "Какой маленький шаг поддержки ты сделаешь сегодня?",
]

SITUATION_STEPS = [
    "Карта 1 — где я сейчас: что в этой карте отзывается твоей ситуации?",
    "Карта 2 — что мешает: что ты здесь узнаёшь про препятствие?",
    "Карта 3 — что поможет: какой ресурс или действие ты видишь?",
    "Сформулируй одним-двумя предложениями свой вывод и первый маленький шаг.",
]


def onboarding_text() -> str:
    return (
        "Привет! Я бережный бот для саморефлексии через метафорические карты.\n"
        "Это не гадание и не психотерапия: я не ставлю диагнозы и не даю готовые истины.\n"
        "Команды: /day_card, /check_in, /situation, /save_insight, /history, /patterns, /metrics, /cancel"
    )


def day_card_intro() -> str:
    card = pick_day_card()
    return (
        f"Твоя карта дня: «{card.title}».\n"
        f"Фокус-вопрос: {card.prompt}\n\n"
        "Что в этой карте откликнулось тебе первым?"
    )


def check_in_intro() -> str:
    card = pick_day_card()
    return f"Быстрый чек-ин. Карта: «{card.title}».\nПодсказка: {card.prompt}\n\n{CHECK_IN_STEPS[0]}"


def situation_intro() -> str:
    cards = pick_spread_cards(3)
    return (
        "Разбор ситуации (3 карты):\n"
        f"1) Где я — «{cards[0].title}»\n"
        f"   Вопрос: {cards[0].prompt}\n"
        f"2) Что мешает — «{cards[1].title}»\n"
        f"   Вопрос: {cards[1].prompt}\n"
        f"3) Что поможет — «{cards[2].title}»\n"
        f"   Вопрос: {cards[2].prompt}\n\n"
        f"{SITUATION_STEPS[0]}"
    )


def render_check_in_summary(answers: list[str]) -> tuple[str, str]:
    emotion = answers[0] if len(answers) > 0 else ""
    meaning = answers[1] if len(answers) > 1 else ""
    step = answers[2] if len(answers) > 2 else ""
    insight = f"Чувство: {emotion}. Важно: {meaning}."
    return insight, step


def render_situation_summary(answers: list[str]) -> tuple[str, str]:
    where_i_am = answers[0] if len(answers) > 0 else ""
    blocker = answers[1] if len(answers) > 1 else ""
    resource = answers[2] if len(answers) > 2 else ""
    conclusion = answers[3] if len(answers) > 3 else ""
    insight = (
        f"Где я: {where_i_am}\n"
        f"Что мешает: {blocker}\n"
        f"Что поможет: {resource}\n"
        f"Вывод: {conclusion}"
    )
    return insight, conclusion


def render_patterns_summary(patterns: list[tuple[str, int]]) -> str:
    if not patterns:
        return "Пока мало данных для паттернов. Сохрани 3-5 инсайтов и возвращайся к /patterns."

    lines = ["Повторяющиеся темы в твоих последних инсайтах:"]
    for idx, (token, score) in enumerate(patterns, start=1):
        lines.append(f"{idx}. {token} — {score} раз")
    lines.append("Это не диагноз, а мягкая подсказка, куда ты часто возвращаешь внимание.")
    return "\n".join(lines)
