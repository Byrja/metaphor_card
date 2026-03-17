import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from app.config import load_settings
from app.content import ContentService
from app.db import Database
from app.events import log_event, setup_event_logger
from app.memory import PatternScore, extract_theme_scores
from app.reminder import build_nudge
from app.safety import CRISIS_REPLY, MEDIUM_RISK_REPLY, assess_text_risk

SITUATION_PROMPTS = [
    "Карта 1 — где ты сейчас.",
    "Карта 2 — что мешает.",
    "Карта 3 — что поможет.",
]


class BotState:
    def __init__(self) -> None:
        self.last_session_by_user: dict[int, int] = {}
        self.pending_insight_by_user: dict[int, str] = {}


state = BotState()


def format_history(rows) -> str:
    if not rows:
        return "Пока нет сохранённых инсайтов."

    parts = ["Твои последние инсайты:"]
    for idx, row in enumerate(rows, start=1):
        step = f" | шаг: {row['small_step_text']}" if row["small_step_text"] else ""
        parts.append(f"{idx}) [{row['scenario_type']}] {row['insight_text']}{step}")
    return "\n".join(parts)


def format_patterns(rows) -> str:
    if not rows:
        return "Пока мало данных для паттернов. Сохрани ещё 2-3 инсайта."
    lines = ["Повторяющиеся темы в твоих последних инсайтах:"]
    for idx, row in enumerate(rows, start=1):
        pct = round(float(row["score"]) * 100)
        lines.append(f"{idx}) {row['pattern_key']} — {pct}%")
    lines.append("Если хочешь, получи мягкую подсказку: /nudge")
    return "\n".join(lines)


def top_pattern_from_rows(rows) -> PatternScore | None:
    if not rows:
        return None
    top = rows[0]
    return PatternScore(key=str(top["pattern_key"]), score=float(top["score"]))


def rebuild_patterns(db: Database, user_id: int) -> None:
    texts = db.get_insight_texts_for_patterns(user_id, limit=50)
    scores = extract_theme_scores(texts)
    db.replace_user_patterns(user_id, [(item.key, item.score) for item in scores])


async def run_safety_guard(db: Database, user_telegram_id: int, user_id: int, text: str) -> str | None:
    decision = assess_text_risk(text)
    if decision.risk_level == "low":
        return None

    session_id = state.last_session_by_user.get(user_telegram_id)
    payload = json.dumps({"matched_markers": decision.matched_markers}, ensure_ascii=False)
    db.log_safety_event(
        user_id=user_id,
        risk_level=decision.risk_level,
        trigger_source="rule",
        trigger_payload_json=payload,
        session_id=session_id,
    )
    log_event(
        "safety_triggered",
        user_id=user_id,
        session_id=session_id,
        risk_level=decision.risk_level,
        trigger_source="rule",
    )

    if session_id:
        db.escalate_session(session_id)
        log_event("safety_escalated", user_id=user_id, session_id=session_id)

    if decision.risk_level == "high":
        return CRISIS_REPLY
    return MEDIUM_RISK_REPLY


def register_handlers(dp: Dispatcher, db: Database, content: ContentService) -> None:
    @dp.message(Command("start"))
    async def start(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        log_event("user_started", user_id=user_id)
        await message.answer(
            "Привет. Я бот для бережной саморефлексии через метафорические карты.\n"
            "Это не гадание и не психотерапия.\n\n"
            "Команды:\n"
            "/day — карта дня\n"
            "/checkin — быстрый чек-ин\n"
            "/situation — разбор ситуации (3 карты)\n"
            "/insight <текст> — сохранить инсайт\n"
            "/history — история\n"
            "/patterns — повторяющиеся темы\n"
            "/nudge — мягкая подсказка по главной теме"
        )

    @dp.message(Command("day"))
    async def day_card(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        session_id = db.create_session(user_id, "day_card")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="day_card")

        card = content.random_day_card(safety_mode="normal")
        prompt = content.random_prompt("l1")
        state.pending_insight_by_user[user.id] = f"Карта дня: {card.title}"
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="day_card")
        await message.answer(f"Твоя карта дня: {card.title}\n{prompt}")

    @dp.message(Command("checkin"))
    async def checkin(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        session_id = db.create_session(user_id, "check_in")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="check_in")

        prompts = content.checkin_prompts()
        safe_card = content.random_day_card(safety_mode="conservative")
        text = "\n".join(["Быстрый чек-ин (бережный режим):", f"Карта опоры: {safe_card.title}", *prompts])
        state.pending_insight_by_user[user.id] = "Чек-ин: обозначено текущее состояние"
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="check_in")
        await message.answer(text)

    @dp.message(Command("situation"))
    async def situation(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        session_id = db.create_session(user_id, "situation_review")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="situation_review")

        cards = content.random_situation_cards(safety_mode="normal")
        lines = ["Разбор ситуации (3 карты):"]
        for prompt, card in zip(SITUATION_PROMPTS, cards):
            lines.append(f"- {prompt} {card.title}")
        lines.append(f"Углубляющий вопрос: {content.random_prompt('l3')}")
        lines.append("Сформулируй вывод и сохрани через /insight <текст>")
        state.pending_insight_by_user[user.id] = (
            f"Разбор: {cards[0].title} / {cards[1].title} / {cards[2].title}"
        )
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="situation_review")
        await message.answer("\n".join(lines))

    @dp.message(Command("insight"))
    async def insight(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)

        payload = (message.text or "").split(maxsplit=1)
        if len(payload) < 2:
            await message.answer("Добавь текст после команды: /insight мой вывод")
            return

        safety_reply = await run_safety_guard(db, user.id, user_id, payload[1])
        if safety_reply:
            await message.answer(safety_reply)
            return

        session_id = state.last_session_by_user.get(user.id)
        if not session_id:
            session_id = db.create_session(user_id, "day_card")
            db.complete_session(session_id)
            state.last_session_by_user[user.id] = session_id

        db.save_insight(session_id, user_id, payload[1], state.pending_insight_by_user.get(user.id))
        rebuild_patterns(db, user_id)
        log_event("insight_saved", user_id=user_id, session_id=session_id)
        await message.answer("Инсайт сохранён. /history, /patterns или /nudge")

    @dp.message(Command("history"))
    async def history(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_recent_insights(user_id, limit=5)
        log_event("history_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_history(rows))

    @dp.message(Command("patterns"))
    async def patterns(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        log_event("patterns_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_patterns(rows))

    @dp.message(Command("nudge"))
    async def nudge(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        top = top_pattern_from_rows(rows)
        log_event("nudge_requested", user_id=user_id, top_pattern=(top.key if top else None))
        await message.answer(build_nudge(top))

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        safety_reply = await run_safety_guard(db, user.id, user_id, message.text or "")
        if safety_reply:
            await message.answer(safety_reply)
            return

        await message.answer("Я пока понимаю команды. Начни с /start")


async def run() -> None:
    settings = load_settings()
    setup_event_logger(settings.log_level)

    db = Database(settings.database_path)
    db.init_schema()
    log_event("db_schema_initialized")

    content = ContentService()
    log_event("content_loaded", decks_count=len(content.decks), prompt_layers=len(content.layers))

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    register_handlers(dp, db, content)
    await dp.start_polling(bot)
