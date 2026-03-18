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

    async def answer(self, text: str) -> None:
        self.answers.append(text)


def _get_handler(dp: Dispatcher, name: str):
    for handler in dp.message.handlers:
        if getattr(handler.callback, "__name__", "") == name:
            return handler.callback
    raise RuntimeError(f"Handler '{name}' not found")


async def main() -> int:
    state.last_session_by_user.clear()
    state.pending_insight_by_user.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "smoke.sqlite3"
        db = Database(db_path.as_posix())
        db.init_schema()
        content = ContentService("content")
        dp = Dispatcher()
        register_handlers(dp, db, content)

        user = FakeUser(id=4242, username="smoke", full_name="Smoke Test")

        start_handler = _get_handler(dp, "start")
        checkin_handler = _get_handler(dp, "checkin")
        situation_handler = _get_handler(dp, "situation")
        insight_handler = _get_handler(dp, "insight")

        start_message = FakeMessage(user, "/start")
        await start_handler(start_message)
        if not start_message.answers or "саморефлексии" not in start_message.answers[-1]:
            raise RuntimeError("/start smoke failed")
        print("[smoke] /start ok")
        print(start_message.answers[-1])

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
