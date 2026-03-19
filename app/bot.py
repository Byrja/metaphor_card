import json
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai_client import suggest_small_step, summarize_reflection
from app.config import Settings, load_settings
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

logger = logging.getLogger("metaphor_card.bot")

SITUATION_PROMPTS = [
    "Карта 1 — где ты сейчас.",
    "Карта 2 — что мешает.",
    "Карта 3 — что поможет.",
]


class BotState:
    def __init__(self) -> None:
        self.last_session_by_user: dict[int, int] = {}
        self.pending_insight_by_user: dict[int, str] = {}
        self.awaiting_insight_by_user: set[int] = set()


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



def build_ai_appendix(context: dict[str, object], settings: Settings) -> tuple[str, str | None]:
    if not settings.ai_enabled:
        return "", None

    try:
        summary = summarize_reflection(context, settings)
        small_step = suggest_small_step(context, settings)
    except Exception as exc:  # pragma: no cover - defensive guard around user-facing flow
        logger.warning("AI appendix generation crashed; using silent fallback: %s", exc)
        return "", None

    if not summary and not small_step:
        return "", None

    appendix_lines = ["", "AI-резюме:", summary]
    if small_step:
        appendix_lines.extend(["", f"Маленький шаг: {small_step}"])
    return "\n".join(line for line in appendix_lines if line), small_step or None


def register_handlers(dp: Dispatcher, db: Database, content: ContentService, settings: Settings | None = None) -> None:
    settings = settings or load_settings()

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
                [InlineKeyboardButton(text="💾 Сохранить инсайт", callback_data="act:saveinsight")],
            ]
        )

    async def answer_user(message: Message, text: str) -> None:
        await message.answer(text, reply_markup=main_menu())

    async def send_start(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        log_event("user_started", user_id=user_id)
        await answer_user(message, START_TEXT)

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
        await answer_user(message, DAY_CARD_TEXT.format(title=card.title, prompt=prompt))

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
        ai_text, suggested_step = build_ai_appendix(
            {
                "scenario": "checkin",
                "focus": safe_card.title,
                "cards": [safe_card.title],
                "prompts": prompts,
            },
            settings,
        )
        state.pending_insight_by_user[user.id] = suggested_step or "Чек-ин: обозначено текущее состояние"
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="check_in")
        await answer_user(message, text + ai_text)

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
        focus_prompt = content.random_prompt("l3")
        lines.append(SITUATION_QUESTION.format(prompt=focus_prompt))
        lines.append(SITUATION_SAVE_HINT)
        ai_text, suggested_step = build_ai_appendix(
            {
                "scenario": "situation",
                "cards": [card.title for card in cards],
                "prompts": [focus_prompt],
                "focus": cards[-1].title,
            },
            settings,
        )
        state.pending_insight_by_user[user.id] = (
            suggested_step or f"Разбор: {cards[0].title} / {cards[1].title} / {cards[2].title}"
        )
        db.complete_session(session_id)
        log_event("session_completed", user_id=user_id, session_id=session_id, scenario_type="situation_review")
        await answer_user(message, "\n".join(lines) + ai_text)

    async def send_history(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_recent_insights(user_id, limit=5)
        log_event("history_opened", user_id=user_id, rows_count=len(rows))
        await answer_user(message, format_history(rows))

    async def send_patterns(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        log_event("patterns_opened", user_id=user_id, rows_count=len(rows))
        await answer_user(message, format_patterns(rows))

    async def send_nudge(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        top = top_pattern_from_rows(rows)
        log_event("nudge_requested", user_id=user_id, top_pattern=(top.key if top else None))
        await answer_user(message, build_nudge(top))

    async def send_save_prompt(message: Message) -> None:
        user = message.from_user
        assert user is not None
        state.awaiting_insight_by_user.add(user.id)
        await message.answer("✍️ Напиши одним сообщением свой инсайт — я сохраню его в историю.", reply_markup=main_menu())

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
            await answer_user(message, INSIGHT_USAGE_TEXT)
            return

        safety_reply = await run_safety_guard(db, user.id, user_id, payload[1])
        if safety_reply:
            await answer_user(message, safety_reply)
            return

        session_id = state.last_session_by_user.get(user.id)
        if not session_id:
            session_id = db.create_session(user_id, "day_card")
            db.complete_session(session_id)
            state.last_session_by_user[user.id] = session_id

        db.save_insight(session_id, user_id, payload[1], state.pending_insight_by_user.get(user.id))
        rebuild_patterns(db, user_id)
        log_event("insight_saved", user_id=user_id, session_id=session_id)
        await answer_user(message, INSIGHT_SAVED_TEXT)

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

        _, _, action = (callback.data or "").partition(":")
        mapping = {
            "day": send_day_card,
            "checkin": send_checkin,
            "situation": send_situation,
            "history": send_history,
            "patterns": send_patterns,
            "nudge": send_nudge,
            "saveinsight": send_save_prompt,
        }
        handler = mapping.get(action)
        if handler is None:
            logger.warning("Unknown callback action: %r", callback.data)
            await callback.answer("Неизвестное действие", show_alert=False)
            await answer_user(callback.message, UNKNOWN_COMMAND_TEXT)
            return
        await callback.answer()
        await handler(callback.message)

    @dp.callback_query()
    async def unknown_callback(callback: CallbackQuery) -> None:
        if callback.message is not None:
            logger.warning("Broken callback data received: %r", callback.data)
            await answer_user(callback.message, UNKNOWN_COMMAND_TEXT)
        await callback.answer("Неизвестное действие", show_alert=False)

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        user = message.from_user
        assert user is not None

        if user.id in state.awaiting_insight_by_user and (message.text or "").strip():
            message.text = f"/insight {(message.text or '').strip()}"
            await insight(message)
            return

        user_id = db.upsert_user(user.id, user.username, user.full_name)
        safety_reply = await run_safety_guard(db, user.id, user_id, message.text or "")
        if safety_reply:
            await answer_user(message, safety_reply)
            return

        await answer_user(message, UNKNOWN_COMMAND_TEXT)


async def run(settings=None) -> None:
    settings = settings or load_settings()
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
        approved_cards=list(content.approved_card_codes),
    )

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    register_handlers(dp, db, content, settings)
    await dp.start_polling(bot)
