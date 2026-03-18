import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import load_settings
from app.content import ContentService
from app.db import Database
from app.events import log_event, setup_event_logger
from app.memory import PatternScore, extract_theme_scores
from app.reminder import build_nudge
from app.safety import CRISIS_REPLY, MEDIUM_RISK_REPLY, assess_text_risk
from app.ux_copy import (
    CHECKIN_CARD,
    CHECKIN_TITLE,
    DAY_CARD_TEXT,
    HISTORY_EMPTY_TEXT,
    HISTORY_STEP_LABEL,
    HISTORY_TITLE,
    INSIGHT_SAVED_TEXT,
    INSIGHT_USAGE_TEXT,
    PATTERNS_EMPTY_TEXT,
    PATTERNS_HINT,
    PATTERNS_TITLE,
    SITUATION_QUESTION,
    SITUATION_SAVE_HINT,
    SITUATION_TITLE,
    START_TEXT,
    UNKNOWN_COMMAND_TEXT,
)

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
        return HISTORY_EMPTY_TEXT

    parts = [HISTORY_TITLE]
    for idx, row in enumerate(rows, start=1):
        step = f" | {HISTORY_STEP_LABEL}: {row['small_step_text']}" if row["small_step_text"] else ""
        parts.append(f"{idx}) [{row['scenario_type']}] {row['insight_text']}{step}")
    return "\n".join(parts)


def format_patterns(rows) -> str:
    if not rows:
        return PATTERNS_EMPTY_TEXT
    lines = [PATTERNS_TITLE]
    for idx, row in enumerate(rows, start=1):
        pct = round(float(row["score"]) * 100)
        lines.append(f"{idx}) {row['pattern_key']} — {pct}%")
    lines.append(PATTERNS_HINT)
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
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🃏 Карта дня", callback_data="act:day"),
                    InlineKeyboardButton(text="🫶 Чек-ин", callback_data="act:checkin"),
                ],
                [InlineKeyboardButton(text="🔎 Разбор ситуации", callback_data="act:situation")],
                [
                    InlineKeyboardButton(text="🧠 Паттерны", callback_data="act:patterns"),
                    InlineKeyboardButton(text="📚 История", callback_data="act:history"),
                ],
                [InlineKeyboardButton(text="✨ Мягкая подсказка", callback_data="act:nudge")],
            ]
        )

    async def send_start(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        log_event("user_started", user_id=user_id)
        await message.answer(START_TEXT, reply_markup=main_menu())

    async def send_day_card(message: Message) -> None:
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
        await message.answer(DAY_CARD_TEXT.format(title=card.title, prompt=prompt), reply_markup=main_menu())

    async def send_checkin(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        session_id = db.create_session(user_id, "check_in")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="check_in")

        prompts = content.checkin_prompts()
        safe_card = content.random_day_card(safety_mode="conservative")
        text = "\n".join([CHECKIN_TITLE, CHECKIN_CARD.format(title=safe_card.title), *prompts])
        state.pending_insight_by_user[user.id] = "Чек-ин: обозначено текущее состояние"
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="check_in")
        await message.answer(text, reply_markup=main_menu())

    async def send_situation(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        session_id = db.create_session(user_id, "situation_review")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="situation_review")

        cards = content.random_situation_cards(safety_mode="normal")
        lines = [SITUATION_TITLE]
        for prompt, card in zip(SITUATION_PROMPTS, cards):
            lines.append(f"- {prompt} {card.title}")
        lines.append(SITUATION_QUESTION.format(prompt=content.random_prompt("l3")))
        lines.append(SITUATION_SAVE_HINT)
        state.pending_insight_by_user[user.id] = (
            f"Разбор: {cards[0].title} / {cards[1].title} / {cards[2].title}"
        )
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="situation_review")
        await message.answer("\n".join(lines), reply_markup=main_menu())

    async def send_history(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_recent_insights(user_id, limit=5)
        log_event("history_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_history(rows), reply_markup=main_menu())

    async def send_patterns(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        log_event("patterns_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_patterns(rows), reply_markup=main_menu())

    async def send_nudge(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        top = top_pattern_from_rows(rows)
        log_event("nudge_requested", user_id=user_id, top_pattern=(top.key if top else None))
        await message.answer(build_nudge(top), reply_markup=main_menu())

    @dp.message(Command("start"))
    async def start(message: Message) -> None:
        await send_start(message)

    @dp.message(Command("day"))
    async def day_card(message: Message) -> None:
        await send_day_card(message)

    @dp.message(Command("checkin"))
    async def checkin(message: Message) -> None:
        await send_checkin(message)

    @dp.message(Command("situation"))
    async def situation(message: Message) -> None:
        await send_situation(message)

    @dp.message(Command("insight"))
    async def insight(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)

        payload = (message.text or "").split(maxsplit=1)
        if len(payload) < 2:
            await message.answer(INSIGHT_USAGE_TEXT, reply_markup=main_menu())
            return

        safety_reply = await run_safety_guard(db, user.id, user_id, payload[1])
        if safety_reply:
            await message.answer(safety_reply, reply_markup=main_menu())
            return

        session_id = state.last_session_by_user.get(user.id)
        if not session_id:
            session_id = db.create_session(user_id, "day_card")
            db.complete_session(session_id)
            state.last_session_by_user[user.id] = session_id

        db.save_insight(session_id, user_id, payload[1], state.pending_insight_by_user.get(user.id))
        rebuild_patterns(db, user_id)
        log_event("insight_saved", user_id=user_id, session_id=session_id)
        await message.answer(INSIGHT_SAVED_TEXT, reply_markup=main_menu())

    @dp.message(Command("history"))
    async def history(message: Message) -> None:
        await send_history(message)

    @dp.message(Command("patterns"))
    async def patterns(message: Message) -> None:
        await send_patterns(message)

    @dp.message(Command("nudge"))
    async def nudge(message: Message) -> None:
        await send_nudge(message)

    @dp.callback_query(F.data.startswith("act:"))
    async def action_menu(callback: CallbackQuery) -> None:
        if callback.message is None:
            await callback.answer()
            return
        action = (callback.data or "").split(":", 1)[1]
        mapping = {
            "day": send_day_card,
            "checkin": send_checkin,
            "situation": send_situation,
            "history": send_history,
            "patterns": send_patterns,
            "nudge": send_nudge,
        }
        handler = mapping.get(action)
        if handler is None:
            await callback.answer("Неизвестное действие", show_alert=False)
            return
        await callback.answer()
        await handler(callback.message)

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        safety_reply = await run_safety_guard(db, user.id, user_id, message.text or "")
        if safety_reply:
            await message.answer(safety_reply, reply_markup=main_menu())
            return

        await message.answer(UNKNOWN_COMMAND_TEXT, reply_markup=main_menu())


async def run() -> None:
    settings = load_settings()
    setup_event_logger(settings.log_level)

    db = Database(settings.database_path)
    db.init_schema()
    log_event("db_schema_initialized", database_path=settings.database_path, app_env=settings.app_env)

    content = ContentService(settings.content_root)
    log_event(
        "content_loaded",
        decks_count=len(content.decks),
        prompt_layers=len(content.layers),
        content_root=settings.content_root,
        using_fallback=content.using_fallback,
    )

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    register_handlers(dp, db, content)
    await dp.start_polling(bot)
