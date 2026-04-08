import json
from dataclasses import dataclass, field
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
    PATTERNS_EMPTY_TEXT,
    PATTERNS_HINT,
    PATTERNS_TITLE,
    SITUATION_TITLE,
    START_TEXT,
    UNKNOWN_COMMAND_TEXT,
)

PREFS_PATH = Path('/srv/openclaw-bus/metaphor_card/state/session_prefs.json')

SITUATION_PROMPTS = [
    "Карта 1 — где ты сейчас.",
    "Карта 2 — что мешает.",
    "Карта 3 — что поможет.",
]

SESSION_STEPS = (
    ("react", "Что ты заметил(а) или почувствовал(а) первым, когда увидел(а) карту?", "l1"),
    ("relate", "На что это похоже в твоей текущей ситуации сегодня?", "l2"),
    ("deepen", "Что в этом сейчас самое важное, острое или непростое?", "l3"),
    ("step", "Какой маленький и реалистичный шаг на сегодня здесь просится?", "l4"),
)

QUESTION_BANK = {
    "soft": {
        "short": (
            "Что на карте откликается тебе прямо сейчас?",
            "Какой самый бережный шаг ты можешь сделать сегодня для себя?",
            "",
            "",
        ),
        "medium": (
            "Что на карте откликается тебе прямо сейчас?",
            "С чем в твоей жизни это мягко перекликается?",
            "Что здесь важно признать и поддержать в себе?",
            "",
        ),
        "deep": (
            "Что на карте откликается тебе прямо сейчас?",
            "С чем в твоей жизни это мягко перекликается?",
            "Какую твою потребность эта карта подсвечивает?",
            "Какой бережный, но конкретный шаг ты сделаешь сегодня?",
        ),
    },
    "balance": {
        "short": (
            "Что ты первым заметил(а) на карте?",
            "Какой маленький реалистичный шаг ты сделаешь сегодня?",
            "",
            "",
        ),
        "medium": (
            "Что ты первым заметил(а) на карте?",
            "С чем это больше всего связано в твоей жизни сейчас (работа/отношения/деньги/самочувствие)?",
            "Что здесь сейчас самое важное и о чём нельзя промолчать?",
            "",
        ),
        "deep": (
            "Что ты первым заметил(а) на карте?",
            "Где это уже проявляется в твоей реальности сегодня?",
            "Какой внутренний конфликт или страх тут поднимается?",
            "Какой конкретный шаг ты сделаешь сегодня и во сколько?",
        ),
    },
    "coach": {
        "short": (
            "Что на карте бьёт в точку прямо сейчас?",
            "Какой один шаг ты сделаешь сегодня до конца дня?",
            "",
            "",
        ),
        "medium": (
            "Что на карте бьёт в точку прямо сейчас?",
            "Где это уже проявляется в твоих действиях?",
            "Какой барьер мешает тебе сдвинуться?",
            "",
        ),
        "deep": (
            "Что на карте бьёт в точку прямо сейчас?",
            "Какая повторяющаяся модель поведения здесь видна?",
            "Что ты теряешь, если оставишь всё как есть?",
            "Какой конкретный шаг ты фиксируешь на сегодня (когда и как)?",
        ),
    },
}

DEPTH_STEP_COUNT = {"short": 2, "medium": 3, "deep": 4}

SKIPPED_ANSWER = "Пропущено"

MAK_INFO_TEXT = (
    "Что такое МАК?\n"
    "Метафорические ассоциативные карты (МАК) — это инструмент самопознания.\n"
    "Ты смотришь на изображение и описываешь свои чувства, мысли и ассоциации.\n\n"
    "Главный принцип: карта значит то, что ты в ней видишь.\n"
    "Здесь нет правильных или неправильных ответов.\n\n"
    "МАК не предсказывают будущее и не ставят диагнозы.\n"
    "Они помогают лучше понять своё состояние и увидеть новый взгляд на ситуацию."
)


@dataclass
class MiniSession:
    user_id: int
    session_id: int
    scenario_type: str
    card_titles: list[str]
    card_caption: str
    current_step: int = 0
    answers: dict[str, str] = field(default_factory=dict)
    saved: bool = False
    final_summary: str | None = None
    small_step: str | None = None


class BotState:
    def __init__(self) -> None:
        self.last_session_by_user: dict[int, int] = {}
        self.pending_insight_by_user: dict[int, str] = {}
        self.awaiting_insight_by_user: set[int] = set()
        self.active_session_by_user: dict[int, MiniSession] = {}
        self.completed_session_by_user: dict[int, MiniSession] = {}
        self.session_mode_by_user: dict[int, str] = {}
        self.session_depth_by_user: dict[int, str] = {}


state = BotState()


def load_session_prefs() -> None:
    try:
        if not PREFS_PATH.exists():
            return
        data = json.loads(PREFS_PATH.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return
        modes = data.get('mode_by_user', {}) or {}
        depths = data.get('depth_by_user', {}) or {}
        state.session_mode_by_user = {int(k): v for k, v in modes.items() if v in {'soft', 'balance', 'coach'}}
        state.session_depth_by_user = {int(k): v for k, v in depths.items() if v in {'short', 'medium', 'deep'}}
    except Exception:
        pass


def save_session_prefs() -> None:
    try:
        PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'mode_by_user': {str(k): v for k, v in state.session_mode_by_user.items()},
            'depth_by_user': {str(k): v for k, v in state.session_depth_by_user.items()},
        }
        PREFS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def get_mode(user_telegram_id: int) -> str:
    return state.session_mode_by_user.get(user_telegram_id, "balance")


def set_mode(user_telegram_id: int, mode: str) -> None:
    if mode in {"soft", "balance", "coach"}:
        state.session_mode_by_user[user_telegram_id] = mode
        save_session_prefs()


def mode_label(mode: str) -> str:
    return {"soft": "мягко", "balance": "баланс", "coach": "коуч"}.get(mode, "баланс")


def mode_safety(mode: str) -> str:
    return "conservative" if mode == "soft" else "normal"


def get_depth(user_telegram_id: int) -> str:
    return state.session_depth_by_user.get(user_telegram_id, "medium")


def set_depth(user_telegram_id: int, depth: str) -> None:
    if depth in {"short", "medium", "deep"}:
        state.session_depth_by_user[user_telegram_id] = depth
        save_session_prefs()


def depth_label(depth: str) -> str:
    return {"short": "коротко", "medium": "средне", "deep": "глубоко"}.get(depth, "средне")


def active_steps(user_telegram_id: int) -> tuple[tuple[str, str, str], ...]:
    mode = get_mode(user_telegram_id)
    depth = get_depth(user_telegram_id)
    leads = QUESTION_BANK.get(mode, QUESTION_BANK["balance"]).get(depth, QUESTION_BANK["balance"]["medium"])
    steps = list(SESSION_STEPS)
    for i in range(len(steps)):
        key, _, layer = steps[i]
        lead = leads[i] if i < len(leads) and leads[i] else SESSION_STEPS[i][1]
        steps[i] = (key, lead, layer)
    count = DEPTH_STEP_COUNT.get(depth, 3)
    return tuple(steps[:count])


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


def session_step_text(user_telegram_id: int, step_index: int, content: ContentService) -> str:
    steps = active_steps(user_telegram_id)
    _, lead, layer = steps[step_index]
    return f"Шаг {step_index + 1}/{len(steps)}. {lead}\nПодсказка: {content.random_prompt(layer)}"


def build_session_summary(session: MiniSession) -> tuple[str, str | None]:
    react = session.answers.get("react", SKIPPED_ANSWER)
    relate = session.answers.get("relate", SKIPPED_ANSWER)
    deepen = session.answers.get("deepen", SKIPPED_ANSWER)
    step = session.answers.get("step", SKIPPED_ANSWER)

    card_focus = ", ".join(f"«{title}»" for title in session.card_titles)
    lines = [
        "Итог мини-сессии:",
        f"Карты: {card_focus}.",
        f"Первый отклик: {react}.",
        f"Связь с ситуацией: {relate}.",
        f"Самое важное: {deepen}.",
    ]
    if step != SKIPPED_ANSWER:
        lines.append(f"Маленький шаг на сегодня: {step}.")
    else:
        lines.append("Маленький шаг на сегодня пока не выбран.")

    return "\n".join(lines), (None if step == SKIPPED_ANSWER else step)


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

    state.active_session_by_user.pop(user_telegram_id, None)

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
                [InlineKeyboardButton(text="⚙️ Режим сессии", callback_data="act:mode")],
                [InlineKeyboardButton(text="💾 Сохранить инсайт", callback_data="act:saveinsight")],
                [InlineKeyboardButton(text="ℹ️ Что такое МАК", callback_data="act:about")],
            ]
        )

    def active_session_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить шаг", callback_data="act:skip_step")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="act:menu")],
            ]
        )

    def session_complete_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💾 Сохранить", callback_data="act:save_session_insight")],
                [InlineKeyboardButton(text="🔁 Ещё карта", callback_data="act:new_card")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="act:menu")],
            ]
        )

    def session_mode_menu(user_telegram_id: int) -> InlineKeyboardMarkup:
        current = get_mode(user_telegram_id)
        depth = get_depth(user_telegram_id)

        def mark(v: str, cur: str) -> str:
            return "✅" if v == cur else "▫️"

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Стиль", callback_data="act:noop")],
                [
                    InlineKeyboardButton(text=f"{mark('soft', current)} мягко", callback_data="act:mode_set_soft"),
                    InlineKeyboardButton(text=f"{mark('balance', current)} баланс", callback_data="act:mode_set_balance"),
                    InlineKeyboardButton(text=f"{mark('coach', current)} коуч", callback_data="act:mode_set_coach"),
                ],
                [InlineKeyboardButton(text="Глубина", callback_data="act:noop")],
                [
                    InlineKeyboardButton(text=f"{mark('short', depth)} коротко", callback_data="act:depth_set_short"),
                    InlineKeyboardButton(text=f"{mark('medium', depth)} средне", callback_data="act:depth_set_medium"),
                    InlineKeyboardButton(text=f"{mark('deep', depth)} глубоко", callback_data="act:depth_set_deep"),
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="act:menu")],
            ]
        )

    def clear_active_session(user_telegram_id: int, *, mark_aborted: bool = False) -> None:
        session = state.active_session_by_user.pop(user_telegram_id, None)
        if session and mark_aborted:
            db.set_session_status(session.session_id, "aborted")

    async def send_card_with_optional_image(message: Message, card, caption: str, reply_markup: InlineKeyboardMarkup) -> None:
        img = (card.image_uri or "").strip()
        if img and not img.startswith("builtin://"):
            path = Path(img)
            if not path.is_absolute():
                path = Path.cwd() / img
            if path.exists():
                await message.answer_photo(photo=FSInputFile(path), caption=caption, reply_markup=reply_markup)
                return
        await message.answer(caption, reply_markup=reply_markup)

    async def send_start(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        log_event("user_started", user_id=user_id)
        await message.answer(START_TEXT, reply_markup=main_menu())

    async def send_about_mak(message: Message) -> None:
        await message.answer(MAK_INFO_TEXT, reply_markup=main_menu())

    def save_completed_session_result(user_telegram_id: int, user_id: int, session: MiniSession) -> None:
        if session.saved:
            return
        summary, small_step = build_session_summary(session)
        db.save_insight(session.session_id, user_id, summary, small_step)
        rebuild_patterns(db, user_id)
        log_event("insight_saved", user_id=user_id, session_id=session.session_id)
        session.saved = True
        session.final_summary = summary
        session.small_step = small_step
        state.pending_insight_by_user[user_telegram_id] = summary
        state.completed_session_by_user[user_telegram_id] = session

    async def finalize_session(message: Message, user_telegram_id: int, user_id: int, session: MiniSession) -> None:
        save_completed_session_result(user_telegram_id, user_id, session)
        db.complete_session(session.session_id)
        log_event("session_completed", user_id=user_id, session_id=session.session_id, scenario_type=session.scenario_type)
        state.active_session_by_user.pop(user_telegram_id, None)
        await message.answer(
            f"{session.final_summary}\n\nСессию уже сохранил в историю — можно закрепить это кнопками ниже.",
            reply_markup=session_complete_menu(),
        )

    async def start_mini_session(message: Message, scenario_type: str) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        clear_active_session(user.id, mark_aborted=True)
        state.awaiting_insight_by_user.discard(user.id)

        session_id = db.create_session(user_id, scenario_type)
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type=scenario_type)

        if scenario_type == "day_card":
            card = content.random_day_card(safety_mode=mode_safety(get_mode(user.id)))
            caption = DAY_CARD_TEXT.format(title=card.title, prompt=session_step_text(user.id, 0, content))
            session = MiniSession(
                user_id=user_id,
                session_id=session_id,
                scenario_type=scenario_type,
                card_titles=[card.title],
                card_caption=caption,
            )
            state.pending_insight_by_user[user.id] = f"Карта дня: {card.title}"
            state.active_session_by_user[user.id] = session
            await send_card_with_optional_image(message, card, caption, active_session_menu())
            return

        cards = content.random_situation_cards(safety_mode=mode_safety(get_mode(user.id)))
        lines = [SITUATION_TITLE]
        for prompt, card in zip(SITUATION_PROMPTS, cards):
            lines.append(f"- {prompt} {card.title}")
        lines.append("")
        lines.append(session_step_text(user.id, 0, content))
        caption = "\n".join(lines)
        session = MiniSession(
            user_id=user_id,
            session_id=session_id,
            scenario_type=scenario_type,
            card_titles=[card.title for card in cards],
            card_caption=caption,
        )
        state.pending_insight_by_user[user.id] = f"Разбор: {' / '.join(session.card_titles)}"
        state.active_session_by_user[user.id] = session
        await send_card_with_optional_image(message, cards[0], caption, active_session_menu())

    async def handle_session_answer(message: Message, *, answer_text: str) -> bool:
        user = message.from_user
        assert user is not None
        session = state.active_session_by_user.get(user.id)
        if session is None:
            return False

        user_id = db.upsert_user(user.id, user.username, user.full_name)
        safety_reply = await run_safety_guard(db, user.id, user_id, answer_text)
        if safety_reply:
            await message.answer(safety_reply, reply_markup=main_menu())
            return True

        steps = active_steps(user.id)
        step_key = steps[session.current_step][0]
        session.answers[step_key] = answer_text.strip() or SKIPPED_ANSWER
        session.current_step += 1

        if session.current_step >= len(steps):
            await finalize_session(message, user.id, user_id, session)
            return True

        await message.answer(session_step_text(user.id, session.current_step, content), reply_markup=active_session_menu())
        return True

    async def send_checkin(message: Message) -> None:
        user = message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        clear_active_session(user.id, mark_aborted=True)
        state.awaiting_insight_by_user.discard(user.id)

        session_id = db.create_session(user_id, "check_in")
        state.last_session_by_user[user.id] = session_id
        log_event("session_started", user_id=user_id, session_id=session_id, scenario_type="check_in")

        card = content.random_day_card(safety_mode=mode_safety(get_mode(user.id)))
        caption = "\n".join([
            CHECKIN_TITLE,
            CHECKIN_CARD.format(title=card.title),
            session_step_text(user.id, 0, content),
        ])

        session = MiniSession(
            user_id=user_id,
            session_id=session_id,
            scenario_type="check_in",
            card_titles=[card.title],
            card_caption=caption,
        )
        state.pending_insight_by_user[user.id] = f"Чек-ин: {card.title}"
        state.active_session_by_user[user.id] = session

        await send_card_with_optional_image(message, card, caption, active_session_menu())

    async def send_day_card(message: Message) -> None:
        await start_mini_session(message, "day_card")

    async def send_situation(message: Message) -> None:
        await start_mini_session(message, "situation_review")

    async def send_history(message: Message) -> None:
        user = message.from_user
        assert user is not None
        clear_active_session(user.id, mark_aborted=False)
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_recent_insights(user_id, limit=5)
        log_event("history_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_history(rows), reply_markup=main_menu())

    async def send_patterns(message: Message) -> None:
        user = message.from_user
        assert user is not None
        clear_active_session(user.id, mark_aborted=False)
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        log_event("patterns_opened", user_id=user_id, rows_count=len(rows))
        await message.answer(format_patterns(rows), reply_markup=main_menu())

    async def send_nudge(message: Message) -> None:
        user = message.from_user
        assert user is not None
        clear_active_session(user.id, mark_aborted=False)
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        rows = db.get_user_patterns(user_id, limit=5)
        top = top_pattern_from_rows(rows)
        log_event("nudge_requested", user_id=user_id, top_pattern=(top.key if top else None))
        await message.answer(build_nudge(top), reply_markup=main_menu())

    async def send_save_prompt(message: Message) -> None:
        user = message.from_user
        assert user is not None
        state.awaiting_insight_by_user.add(user.id)
        await message.answer("✍️ Напиши одним сообщением свой инсайт — я сохраню его в историю.", reply_markup=main_menu())

    @dp.message(Command("start"))
    async def start(message: Message) -> None:
        clear_active_session(message.from_user.id, mark_aborted=True) if message.from_user else None
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
            state.awaiting_insight_by_user.add(user.id)
            await message.answer("✍️ Напиши одним сообщением свой инсайт — я сохраню его в историю.", reply_markup=main_menu())
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
        state.awaiting_insight_by_user.discard(user.id)
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

        user = getattr(callback, "from_user", None) or callback.message.from_user
        assert user is not None
        user_id = db.upsert_user(user.id, user.username, user.full_name)
        action = (callback.data or "").split(":", 1)[1]

        if action == "skip_step":
            session = state.active_session_by_user.get(user.id)
            if session is None:
                await callback.answer("Сейчас нет активного шага.", show_alert=False)
                return
            await callback.answer("Шаг пропущен")
            await handle_session_answer(callback.message, answer_text=SKIPPED_ANSWER)
            return

        if action == "save_session_insight":
            session = state.completed_session_by_user.get(user.id)
            if session is None:
                await callback.answer("Сначала заверши мини-сессию.", show_alert=False)
                return
            save_completed_session_result(user.id, user_id, session)
            await callback.answer("Итог уже сохранён")
            await callback.message.answer(INSIGHT_SAVED_TEXT, reply_markup=main_menu())
            return

        if action == "new_card":
            await callback.answer()
            previous = state.completed_session_by_user.get(user.id)
            scenario_type = previous.scenario_type if previous else "day_card"
            if scenario_type == "situation_review":
                await send_situation(callback.message)
            else:
                await send_day_card(callback.message)
            return

        if action == "menu":
            clear_active_session(user.id, mark_aborted=False)
            await callback.answer()
            if hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(START_TEXT, reply_markup=main_menu())
            else:
                await callback.message.answer(START_TEXT, reply_markup=main_menu())
            return

        if action == "about":
            await callback.answer()
            if hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(MAK_INFO_TEXT, reply_markup=main_menu())
            else:
                await callback.message.answer(MAK_INFO_TEXT, reply_markup=main_menu())
            return

        if action == "mode":
            await callback.answer()
            mode_text = (
                f"⚙️ <b>Настройки сессии</b>\n"
                f"Текущий стиль: <b>{mode_label(get_mode(user.id))}</b>\n"
                f"Текущая глубина: <b>{depth_label(get_depth(user.id))}</b>\n\n"
                "Стиль = как формулируются вопросы.\n"
                "Глубина = сколько шагов будет в сессии."
            )
            if hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(mode_text, reply_markup=session_mode_menu(user.id))
            else:
                await callback.message.answer(mode_text, reply_markup=session_mode_menu(user.id))
            return

        if action == "reroll":
            await callback.answer("Подбираю другую карту…")
            current = state.active_session_by_user.get(user.id)
            if not current:
                await send_day_card(callback.message)
                return
            scenario = current.scenario_type
            clear_active_session(user.id, mark_aborted=True)
            if scenario == "day_card":
                await send_day_card(callback.message)
            elif scenario == "situation_review":
                await send_situation(callback.message)
            elif scenario == "check_in":
                await send_checkin(callback.message)
            else:
                await send_day_card(callback.message)
            return

        if action == "noop":
            await callback.answer()
            return

        if action.startswith("mode_set_"):
            mode = action.replace("mode_set_", "")
            set_mode(user.id, mode)
            await callback.answer("Режим сохранён")
            mode_text = (
                f"✅ Стиль обновлён: <b>{mode_label(get_mode(user.id))}</b>\n"
                f"Глубина: <b>{depth_label(get_depth(user.id))}</b>"
            )
            if hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(mode_text, reply_markup=session_mode_menu(user.id))
            else:
                await callback.message.answer(mode_text, reply_markup=session_mode_menu(user.id))
            return

        if action.startswith("depth_set_"):
            depth = action.replace("depth_set_", "")
            set_depth(user.id, depth)
            await callback.answer("Глубина сохранена")
            mode_text = (
                f"Стиль: <b>{mode_label(get_mode(user.id))}</b>\n"
                f"✅ Глубина обновлена: <b>{depth_label(get_depth(user.id))}</b>"
            )
            if hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(mode_text, reply_markup=session_mode_menu(user.id))
            else:
                await callback.message.answer(mode_text, reply_markup=session_mode_menu(user.id))
            return

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
            await callback.answer("Неизвестное действие", show_alert=False)
            return
        await callback.answer()
        actor = getattr(callback, "from_user", None) or callback.message.from_user
        if hasattr(callback.message, "model_copy"):
            message_for_handler = callback.message.model_copy(update={"from_user": actor})
        else:
            # smoke tests provide FakeMessage without pydantic model_copy
            message_for_handler = callback.message
            try:
                message_for_handler.from_user = actor
            except Exception:
                pass
        await handler(message_for_handler)

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        user = message.from_user
        assert user is not None

        if user.id in state.awaiting_insight_by_user and (message.text or "").strip():
            message.text = f"/insight {(message.text or '').strip()}"
            await insight(message)
            return

        if await handle_session_answer(message, answer_text=message.text or ""):
            return

        user_id = db.upsert_user(user.id, user.username, user.full_name)
        safety_reply = await run_safety_guard(db, user.id, user_id, message.text or "")
        if safety_reply:
            await message.answer(safety_reply, reply_markup=main_menu())
            return

        await message.answer(UNKNOWN_COMMAND_TEXT, reply_markup=main_menu())


async def run(settings=None) -> None:
    settings = settings or load_settings()
    setup_event_logger(settings.log_level)
    load_session_prefs()

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
