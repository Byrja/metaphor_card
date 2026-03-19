from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aiogram import Dispatcher

from app.bot import register_handlers, state
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
        self.answers: list[str] = []
        self.answer_kwargs: list[dict] = []

    async def answer(self, text: str, reply_markup=None, **kwargs) -> None:
        self.answers.append(text)
        payload = dict(kwargs)
        payload["reply_markup"] = reply_markup
        self.answer_kwargs.append(payload)

    async def answer_photo(self, photo, caption: str | None = None, reply_markup=None, **kwargs) -> None:
        self.answers.append(caption or "")
        payload = dict(kwargs)
        payload["reply_markup"] = reply_markup
        payload["photo"] = photo
        self.answer_kwargs.append(payload)


class FakeCallbackQuery:
    def __init__(self, data: str, message: FakeMessage | None) -> None:
        self.data = data
        self.message = message
        self.answer_calls: list[dict] = []

    async def answer(self, text: str | None = None, show_alert: bool | None = None) -> None:
        self.answer_calls.append({"text": text, "show_alert": show_alert})


def _get_handler(handlers, name: str):
    for handler in handlers:
        if getattr(handler.callback, "__name__", "") == name:
            return handler.callback
    raise RuntimeError(f"Handler '{name}' not found")


async def main() -> int:
    state.last_session_by_user.clear()
    state.pending_insight_by_user.clear()
    state.awaiting_insight_by_user.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "smoke.sqlite3"
        db = Database(db_path.as_posix())
        db.init_schema()
        content = ContentService("content")
        dp = Dispatcher()
        register_handlers(dp, db, content)

        user = FakeUser(id=4242, username="smoke", full_name="Smoke Test")

        start_handler = _get_handler(dp.message.handlers, "start")
        checkin_handler = _get_handler(dp.message.handlers, "checkin")
        situation_handler = _get_handler(dp.message.handlers, "situation")
        insight_handler = _get_handler(dp.message.handlers, "insight")
        action_handler = _get_handler(dp.callback_query.handlers, "action_menu")

        start_message = FakeMessage(user, "/start")
        await start_handler(start_message)
        if not start_message.answers or "Бережная саморефлексия" not in start_message.answers[-1]:
            raise RuntimeError("/start smoke failed")
        markup = start_message.answer_kwargs[-1].get("reply_markup")
        callback_data = [button.callback_data for row in markup.inline_keyboard for button in row] if markup else []
        expected_actions = ["act:day", "act:checkin", "act:situation", "act:patterns", "act:history", "act:nudge", "act:saveinsight"]
        if callback_data != expected_actions:
            raise RuntimeError(f"/start inline menu mismatch: {callback_data}")
        print("[smoke] /start ok")
        print(start_message.answers[-1])

        for action in expected_actions:
            callback_message = FakeMessage(user, "/start")
            callback = FakeCallbackQuery(action, callback_message)
            await action_handler(callback)
            if not callback.answer_calls:
                raise RuntimeError(f"{action} callback did not answer")
            if not callback_message.answers:
                raise RuntimeError(f"{action} callback did not render content")
            print(f"[smoke] {action} callback ok")
            print(callback_message.answers[-1])

        unknown_callback = FakeCallbackQuery("act:unknown", FakeMessage(user, "/start"))
        await action_handler(unknown_callback)
        if unknown_callback.answer_calls[-1]["text"] != "Неизвестное действие":
            raise RuntimeError("unknown callback fallback failed")
        print("[smoke] unknown callback fallback ok")

        checkin_message = FakeMessage(user, "/checkin")
        await checkin_handler(checkin_message)
        if not checkin_message.answers or "чек-ин" not in checkin_message.answers[-1].lower():
            raise RuntimeError("/checkin smoke failed")
        print("[smoke] /checkin ok")
        print(checkin_message.answers[-1])

        situation_message = FakeMessage(user, "/situation")
        await situation_handler(situation_message)
        if not situation_message.answers or "ситуацию" not in situation_message.answers[-1].lower():
            raise RuntimeError("/situation smoke failed")
        print("[smoke] /situation ok")
        print(situation_message.answers[-1])

        safety_message = FakeMessage(user, "/insight паника и мне очень страшно")
        await insight_handler(safety_message)
        if not safety_message.answers or "заземлиться" not in safety_message.answers[-1].lower():
            raise RuntimeError("/insight safety smoke failed")
        print("[smoke] /insight safety ok")
        print(safety_message.answers[-1])

        print("[smoke] graceful stop ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
