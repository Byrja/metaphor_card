from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aiogram import Dispatcher

from app.bot import register_handlers, state
from app.config import load_settings
from app.content import ContentService
from app.db import Database


@dataclass
class FakeUser:
    id: int
    username: str
    full_name: str


class FakeMessage:
    def __init__(self, user: FakeUser, text: str) -> None:
        self.from_user = user
        self.text = text
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.answers.append((text, kwargs.get('reply_markup')))


class FakeCallback:
    def __init__(self, message: FakeMessage, data: str | None) -> None:
        self.message = message
        self.data = data
        self.answer_calls: list[tuple[str | None, bool]] = []

    async def answer(self, text: str | None = None, show_alert: bool = False) -> None:
        self.answer_calls.append((text, show_alert))


def _get_message_handler(dp: Dispatcher, name: str):
    for handler in dp.message.handlers:
        if getattr(handler.callback, '__name__', '') == name:
            return handler.callback
    raise RuntimeError(f'message handler {name} not found')


def _get_callback_handler(dp: Dispatcher, name: str):
    for handler in dp.callback_query.handlers:
        if getattr(handler.callback, '__name__', '') == name:
            return handler.callback
    raise RuntimeError(f'callback handler {name} not found')


def test_checkin_appends_ai_block_when_enabled(monkeypatch) -> None:
    async def scenario() -> None:
        state.last_session_by_user.clear()
        state.pending_insight_by_user.clear()
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / 'bot.sqlite3'))
            db.init_schema()
            content = ContentService('content')
            dp = Dispatcher()
            settings = load_settings({'BOT_TOKEN': '123:abc', 'AI_ENABLED': '1', 'OPENROUTER_API_KEY': 'x'})
            register_handlers(dp, db, content, settings)

            monkeypatch.setattr('app.bot.summarize_reflection', lambda context, settings=None: 'AI summary')
            monkeypatch.setattr('app.bot.suggest_small_step', lambda context, settings=None: 'AI step')

            handler = _get_message_handler(dp, 'checkin')
            message = FakeMessage(FakeUser(1, 'u', 'User'), '/checkin')
            await handler(message)

            assert 'AI-резюме' in message.answers[-1][0]
            assert 'AI step' in message.answers[-1][0]
            assert state.pending_insight_by_user[1] == 'AI step'
            assert message.answers[-1][1] is not None

    asyncio.run(scenario())


def test_checkin_keeps_current_text_when_ai_disabled() -> None:
    async def scenario() -> None:
        state.last_session_by_user.clear()
        state.pending_insight_by_user.clear()
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / 'bot.sqlite3'))
            db.init_schema()
            content = ContentService('content')
            dp = Dispatcher()
            settings = load_settings({'BOT_TOKEN': '123:abc', 'AI_ENABLED': '0'})
            register_handlers(dp, db, content, settings)

            handler = _get_message_handler(dp, 'checkin')
            message = FakeMessage(FakeUser(2, 'u2', 'User 2'), '/checkin')
            await handler(message)

            assert 'AI-резюме' not in message.answers[-1][0]
            assert state.pending_insight_by_user[2] == 'Чек-ин: обозначено текущее состояние'

    asyncio.run(scenario())


def test_unknown_callback_is_graceful() -> None:
    async def scenario() -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / 'bot.sqlite3'))
            db.init_schema()
            content = ContentService('content')
            dp = Dispatcher()
            settings = load_settings({'BOT_TOKEN': '123:abc'})
            register_handlers(dp, db, content, settings)

            handler = _get_callback_handler(dp, 'unknown_callback')
            message = FakeMessage(FakeUser(3, 'u3', 'User 3'), 'button')
            callback = FakeCallback(message, 'broken:data')
            await handler(callback)

            assert callback.answer_calls[-1][0] == 'Неизвестное действие'
            assert 'Нажми /start' in message.answers[-1][0]

    asyncio.run(scenario())


def test_checkin_ai_crash_is_swallowed_gracefully(monkeypatch) -> None:
    async def scenario() -> None:
        state.last_session_by_user.clear()
        state.pending_insight_by_user.clear()
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / 'bot.sqlite3'))
            db.init_schema()
            content = ContentService('content')
            dp = Dispatcher()
            settings = load_settings({'BOT_TOKEN': '123:abc', 'AI_ENABLED': '1', 'OPENROUTER_API_KEY': 'x'})
            register_handlers(dp, db, content, settings)

            monkeypatch.setattr('app.bot.summarize_reflection', lambda context, settings=None: (_ for _ in ()).throw(RuntimeError('boom')))
            monkeypatch.setattr('app.bot.suggest_small_step', lambda context, settings=None: 'AI step')

            handler = _get_message_handler(dp, 'checkin')
            message = FakeMessage(FakeUser(4, 'u4', 'User 4'), '/checkin')
            await handler(message)

            assert 'AI-резюме' not in message.answers[-1][0]
            assert state.pending_insight_by_user[4] == 'Чек-ин: обозначено текущее состояние'

    asyncio.run(scenario())
