import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str = "data/metaphor_card.db"
    log_level: str = "INFO"


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is required")
    return Settings(
        bot_token=token,
        database_path=os.getenv("DATABASE_PATH", "data/metaphor_card.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
