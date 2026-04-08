import asyncio
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from aiogram import Dispatcher

from app.bot import register_handlers, set_depth, state
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

    async def answer_photo(self, photo, caption: str | None = None, **kwargs) -> None:
        self.answers.append(caption or "")
        payload = dict(kwargs)
        payload["photo"] = photo
        self.answer_kwargs.append(payload)


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
        state.awaiting_insight_by_user.clear()
        state.active_session_by_user.clear()
        state.completed_session_by_user.clear()
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
                    "act:nudge",
                    "act:mode",
                    "act:saveinsight",
                    "act:about",
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
                "act:nudge": "данных для персональной подсказки мало",
                "act:saveinsight": "напиши одним сообщением свой инсайт",
            }

            for action, expected in action_expectations.items():
                message = FakeMessage(self.user, "/start")
                callback = FakeCallbackQuery(action, message)
                await callback_handler(callback)
                self.assertTrue(message.answers, action)
                self.assertIn(expected.lower(), message.answers[-1].lower(), action)
                self.assertEqual(callback.answer_calls[-1]["text"], None, action)

        asyncio.run(scenario())

    def test_day_mini_session_runs_all_four_steps_and_saves_summary(self):
        async def scenario() -> None:
            day_handler = self._get_message_handler("day_card")
            fallback_handler = self._get_message_handler("fallback")
            set_depth(self.user.id, "deep")

            start = FakeMessage(self.user, "/day")
            await day_handler(start)
            self.assertIn("Шаг 1/", start.answers[-1])

            answers = [
                "Сначала заметил спокойствие.",
                "Это похоже на мой рабочий день сегодня.",
                "Самое острое — страх ошибиться.",
                "Напишу черновик письма до обеда.",
            ]
            last_message = start
            for text in answers:
                last_message = FakeMessage(self.user, text)
                await fallback_handler(last_message)

            self.assertIn("Итог мини-сессии", last_message.answers[-1])
            self.assertIn("Маленький шаг на сегодня: Напишу черновик письма до обеда.", last_message.answers[-1])
            markup = last_message.answer_kwargs[-1]["reply_markup"]
            callback_data = [button.callback_data for row in markup.inline_keyboard for button in row]
            self.assertEqual(
                callback_data,
                ["act:save_session_insight", "act:new_card", "act:menu"],
            )

            user_id = self.db.upsert_user(self.user.id, self.user.username, self.user.full_name)
            rows = self.db.get_recent_insights(user_id, limit=5)
            self.assertEqual(len(rows), 1)
            self.assertIn("Итог мини-сессии", rows[0]["insight_text"])
            self.assertEqual(rows[0]["small_step_text"], "Напишу черновик письма до обеда.")

        asyncio.run(scenario())

    def test_mini_session_safety_interrupts_and_stops_flow(self):
        async def scenario() -> None:
            situation_handler = self._get_message_handler("situation")
            fallback_handler = self._get_message_handler("fallback")

            start = FakeMessage(self.user, "/situation")
            await situation_handler(start)
            self.assertIn("Шаг 1/", start.answers[-1])

            risky = FakeMessage(self.user, "У меня паника и очень страшно")
            await fallback_handler(risky)

            self.assertIn("заземлиться", risky.answers[-1].lower())
            self.assertNotIn(self.user.id, state.active_session_by_user)

            with self.db.connection() as conn:
                status = conn.execute("SELECT status FROM sessions ORDER BY id DESC LIMIT 1").fetchone()["status"]
                safety_count = conn.execute("SELECT COUNT(*) AS c FROM safety_events").fetchone()["c"]
            self.assertEqual(status, "safety_escalated")
            self.assertEqual(safety_count, 1)

        asyncio.run(scenario())

    def test_final_screen_inline_buttons_work(self):
        async def scenario() -> None:
            day_handler = self._get_message_handler("day_card")
            fallback_handler = self._get_message_handler("fallback")
            callback_handler = self._get_callback_handler("action_menu")
            set_depth(self.user.id, "deep")

            await day_handler(FakeMessage(self.user, "/day"))
            for text in [
                "Заметил тепло.",
                "Это похоже на разговор с близким.",
                "Самое важное — попросить поддержку.",
                "Напишу одному человеку вечером.",
            ]:
                await fallback_handler(FakeMessage(self.user, text))

            save_callback = FakeCallbackQuery("act:save_session_insight", FakeMessage(self.user, "done"))
            await callback_handler(save_callback)
            self.assertEqual(save_callback.answer_calls[-1]["text"], "Итог уже сохранён")
            self.assertIn("Сохранил.", save_callback.message.answers[-1])

            new_card_callback = FakeCallbackQuery("act:new_card", FakeMessage(self.user, "done"))
            await callback_handler(new_card_callback)
            self.assertIn("Шаг 1/", new_card_callback.message.answers[-1])

            menu_callback = FakeCallbackQuery("act:menu", FakeMessage(self.user, "done"))
            await callback_handler(menu_callback)
            self.assertEqual(menu_callback.message.answers[-1], START_TEXT)

        asyncio.run(scenario())

    def test_active_session_menu_supports_reroll(self):
        async def scenario() -> None:
            day_handler = self._get_message_handler("day_card")
            callback_handler = self._get_callback_handler("action_menu")

            start = FakeMessage(self.user, "/day")
            await day_handler(start)
            callback_data = [button.callback_data for row in start.answer_kwargs[-1]["reply_markup"].inline_keyboard for button in row]
            self.assertIn("act:reroll", callback_data)

            reroll_callback = FakeCallbackQuery("act:reroll", FakeMessage(self.user, "done"))
            reroll_callback.from_user = self.user
            await callback_handler(reroll_callback)
            self.assertIn("Шаг 1/", reroll_callback.message.answers[-1])

        asyncio.run(scenario())

    def test_unknown_callback_uses_fallback_answer(self):
        async def scenario() -> None:
            callback_handler = self._get_callback_handler("action_menu")
            callback = FakeCallbackQuery("act:unknown", FakeMessage(self.user, "/start"))
            await callback_handler(callback)

            self.assertEqual(callback.answer_calls[-1]["text"], "Неизвестное действие")
            self.assertFalse(callback.message.answers)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
