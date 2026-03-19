import asyncio
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from aiogram import Dispatcher

from app.bot import register_handlers, state
from app.content import ContentService
from app.db import Database
from app.ux_copy import START_TEXT


@dataclass
class FakeUser:
    id: int
    username: str
    full_name: str


class FakeMessage:
    def __init__(self, user: FakeUser, text: str) -> None:
        self.from_user = user
        self.text = text
        self.answers: list[str] = []
        self.answer_kwargs: list[dict] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.answers.append(text)
        self.answer_kwargs.append(kwargs)


class FakeCallbackQuery:
    def __init__(self, data: str, message: FakeMessage | None) -> None:
        self.data = data
        self.message = message
        self.answer_calls: list[dict] = []

    async def answer(self, text: str | None = None, show_alert: bool | None = None) -> None:
        self.answer_calls.append({"text": text, "show_alert": show_alert})


class BotInlineFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        state.last_session_by_user.clear()
        state.pending_insight_by_user.clear()
        state.awaiting_free_text_insight_by_user.clear()
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "test.sqlite3"
        self.db = Database(db_path.as_posix())
        self.db.init_schema()
        self.content = ContentService("content")
        self.dp = Dispatcher()
        register_handlers(self.dp, self.db, self.content)
        self.user = FakeUser(id=99, username="tester", full_name="Test User")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _get_message_handler(self, name: str):
        for handler in self.dp.message.handlers:
            if getattr(handler.callback, "__name__", "") == name:
                return handler.callback
        raise RuntimeError(f"Handler '{name}' not found")

    def _get_callback_handler(self, name: str):
        for handler in self.dp.callback_query.handlers:
            if getattr(handler.callback, "__name__", "") == name:
                return handler.callback
        raise RuntimeError(f"Callback handler '{name}' not found")

    def test_start_menu_exposes_all_inline_actions(self):
        async def scenario() -> None:
            start_handler = self._get_message_handler("start")
            message = FakeMessage(self.user, "/start")
            await start_handler(message)

            self.assertEqual(message.answers[-1], START_TEXT)
            markup = message.answer_kwargs[-1]["reply_markup"]
            callback_data = [button.callback_data for row in markup.inline_keyboard for button in row]
            self.assertEqual(
                callback_data,
                [
                    "act:day",
                    "act:checkin",
                    "act:situation",
                    "act:patterns",
                    "act:history",
                    "act:saveinsight",
                    "act:nudge",
                ],
            )

        asyncio.run(scenario())

    def test_callback_actions_answer_and_render_content(self):
        async def scenario() -> None:
            callback_handler = self._get_callback_handler("action_menu")
            action_expectations = {
                "act:day": "Карта дня:",
                "act:checkin": "чек-ин",
                "act:situation": "ситуацию",
                "act:patterns": "Пока данных мало",
                "act:history": "Пока здесь пусто",
                "act:saveinsight": "Напиши одним сообщением свой инсайт",
                "act:nudge": "данных для персональной подсказки мало",
            }

            for action, expected in action_expectations.items():
                message = FakeMessage(self.user, "/start")
                callback = FakeCallbackQuery(action, message)
                await callback_handler(callback)
                self.assertTrue(message.answers, action)
                self.assertIn(expected.lower(), message.answers[-1].lower(), action)
                self.assertEqual(callback.answer_calls[-1]["text"], None, action)

        asyncio.run(scenario())

    def test_unknown_callback_uses_fallback_answer(self):
        async def scenario() -> None:
            callback_handler = self._get_callback_handler("action_menu")
            callback = FakeCallbackQuery("act:unknown", FakeMessage(self.user, "/start"))
            await callback_handler(callback)

            self.assertEqual(callback.answer_calls[-1]["text"], "Неизвестное действие")
            self.assertFalse(callback.message.answers)

        asyncio.run(scenario())

    def test_saveinsight_callback_marks_user_and_prompts_for_text(self):
        async def scenario() -> None:
            callback_handler = self._get_callback_handler("action_menu")
            message = FakeMessage(self.user, "/start")
            callback = FakeCallbackQuery("act:saveinsight", message)

            await callback_handler(callback)

            self.assertIn(self.user.id, state.awaiting_free_text_insight_by_user)
            self.assertIn("Напиши одним сообщением свой инсайт", message.answers[-1])
            self.assertEqual(callback.answer_calls[-1]["text"], None)

        asyncio.run(scenario())

    def test_free_text_after_saveinsight_callback_is_saved_to_history(self):
        async def scenario() -> None:
            callback_handler = self._get_callback_handler("action_menu")
            fallback_handler = self._get_message_handler("fallback")

            start_message = FakeMessage(self.user, "/start")
            callback = FakeCallbackQuery("act:saveinsight", start_message)
            await callback_handler(callback)

            insight_message = FakeMessage(self.user, "Сегодня мне важно делать паузу")
            await fallback_handler(insight_message)

            saved_user_id = self.db.upsert_user(self.user.id, self.user.username, self.user.full_name)
            rows = self.db.get_recent_insights(saved_user_id, limit=5)

            self.assertEqual(rows[0]["insight_text"], "Сегодня мне важно делать паузу")
            self.assertNotIn(self.user.id, state.awaiting_free_text_insight_by_user)
            self.assertIn("Сохранил.", insight_message.answers[-1])
            markup = insight_message.answer_kwargs[-1]["reply_markup"]
            callback_data = [button.callback_data for row in markup.inline_keyboard for button in row]
            self.assertIn("act:saveinsight", callback_data)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
