from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

DEFAULT_DATABASE_PATH = "data/metaphor_card.db"
DEFAULT_CONTENT_ROOT = "content"
DEFAULT_ENV = "dev"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_AI_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_AI_TIMEOUT_SEC = 12.0
VALID_ENVS = {"dev", "prod"}
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
VALID_AI_PROVIDERS = {"openrouter"}
PLACEHOLDER_BOT_TOKENS = {
    "put_your_telegram_token_here",
    "your_bot_token_here",
    "changeme",
}


class SettingsError(RuntimeError):
    """Raised when required environment configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str = DEFAULT_DATABASE_PATH
    log_level: str = DEFAULT_LOG_LEVEL
    app_env: str = DEFAULT_ENV
    content_root: str = DEFAULT_CONTENT_ROOT
    ai_enabled: bool = False
    ai_provider: str = DEFAULT_AI_PROVIDER
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    ai_timeout_sec: float = DEFAULT_AI_TIMEOUT_SEC


def _normalize_bot_token(raw_value: str | None) -> str:
    token = (raw_value or "").strip()
    if not token or token.lower() in PLACEHOLDER_BOT_TOKENS:
        raise SettingsError(
            "BOT_TOKEN is required. Set a real Telegram bot token in the environment or .env file."
        )
    return token


def _normalize_log_level(raw_value: str | None) -> str:
    level = (raw_value or DEFAULT_LOG_LEVEL).strip().upper() or DEFAULT_LOG_LEVEL
    if level not in VALID_LOG_LEVELS:
        return DEFAULT_LOG_LEVEL
    return level


def _normalize_app_env(raw_value: str | None) -> str:
    app_env = (raw_value or DEFAULT_ENV).strip().lower() or DEFAULT_ENV
    if app_env not in VALID_ENVS:
        valid = ", ".join(sorted(VALID_ENVS))
        raise SettingsError(f"APP_ENV must be one of: {valid}.")
    return app_env


def _normalize_database_path(raw_value: str | None) -> str:
    path = (raw_value or DEFAULT_DATABASE_PATH).strip() or DEFAULT_DATABASE_PATH
    if path == ":memory:":
        return path

    normalized = Path(path).expanduser()
    parent = normalized.parent
    if str(parent) in {"", "."}:
        return str(normalized)
    return str(normalized)


def _normalize_content_root(raw_value: str | None) -> str:
    root = (raw_value or DEFAULT_CONTENT_ROOT).strip() or DEFAULT_CONTENT_ROOT
    return str(Path(root).expanduser())


def _normalize_bool(raw_value: str | None, *, default: bool = False) -> bool:
    value = (raw_value or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _normalize_ai_provider(raw_value: str | None) -> str:
    provider = (raw_value or DEFAULT_AI_PROVIDER).strip().lower() or DEFAULT_AI_PROVIDER
    if provider not in VALID_AI_PROVIDERS:
        valid = ", ".join(sorted(VALID_AI_PROVIDERS))
        raise SettingsError(f"AI_PROVIDER must be one of: {valid}.")
    return provider


def _normalize_timeout(raw_value: str | None) -> float:
    value = (raw_value or "").strip()
    if not value:
        return DEFAULT_AI_TIMEOUT_SEC
    try:
        timeout = float(value)
    except ValueError as exc:
        raise SettingsError("AI_TIMEOUT_SEC must be a positive number.") from exc
    if timeout <= 0:
        raise SettingsError("AI_TIMEOUT_SEC must be a positive number.")
    return timeout


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    load_dotenv()
    env = environ if environ is not None else os.environ

    return Settings(
        bot_token=_normalize_bot_token(env.get("BOT_TOKEN")),
        database_path=_normalize_database_path(env.get("DATABASE_PATH")),
        log_level=_normalize_log_level(env.get("LOG_LEVEL")),
        app_env=_normalize_app_env(env.get("APP_ENV")),
        content_root=_normalize_content_root(env.get("CONTENT_ROOT")),
        ai_enabled=_normalize_bool(env.get("AI_ENABLED"), default=False),
        ai_provider=_normalize_ai_provider(env.get("AI_PROVIDER")),
        openrouter_api_key=(env.get("OPENROUTER_API_KEY") or "").strip(),
        openrouter_model=(env.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip()
        or DEFAULT_OPENROUTER_MODEL,
        ai_timeout_sec=_normalize_timeout(env.get("AI_TIMEOUT_SEC")),
    )
