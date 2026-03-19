from __future__ import annotations

import json
import logging
import socket
from typing import Any
from urllib import error, request

from app.config import Settings, load_settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_PROMPT = (
    "Ты помогаешь бережной саморефлексии через метафорические карты. "
    "Не ставь диагнозы, не давай жёстких указаний, не обещай чудес. "
    "Пиши коротко, мягко, по-русски."
)

logger = logging.getLogger("metaphor_card.ai")


class AIClientError(RuntimeError):
    """Raised when the AI provider returns unusable data."""


def summarize_reflection(context: dict[str, Any]) -> str:
    return _generate(
        task="summary",
        context=context,
        fallback=_fallback_summary(context),
        instruction=(
            "Сделай 1-2 предложения с мягким отражением увиденного в сценарии. "
            "Не используй буллиты и не повторяй служебные поля."
        ),
    )


def suggest_small_step(context: dict[str, Any]) -> str:
    return _generate(
        task="small_step",
        context=context,
        fallback=_fallback_small_step(context),
        instruction=(
            "Предложи один очень маленький и безопасный шаг на сегодня. "
            "До 140 символов, без давления и без императива в жёсткой форме."
        ),
    )


def _generate(task: str, context: dict[str, Any], fallback: str, instruction: str) -> str:
    settings = load_settings()
    if not settings.ai_enabled:
        return fallback
    if settings.ai_provider != "openrouter":
        logger.warning("Unsupported AI provider '%s'; using fallback", settings.ai_provider)
        return fallback
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY is empty; using fallback")
        return fallback

    try:
        response_text = _request_openrouter(context=context, instruction=instruction, settings=settings)
    except (AIClientError, error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        logger.warning("AI %s request failed: %s", task, exc)
        return fallback

    cleaned = " ".join(response_text.split())
    if not cleaned:
        return fallback
    return cleaned


def _request_openrouter(*, context: dict[str, Any], instruction: str, settings: Settings) -> str:
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": instruction,
                        "context": context,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.4,
    }
    req = request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Byrja/metaphor_card",
            "X-Title": "metaphor_card",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=settings.ai_timeout_sec) as response:
        raw = response.read().decode("utf-8")

    try:
        data = json.loads(raw)
        choices = data["choices"]
        message = choices[0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise AIClientError("OpenRouter response is missing choices[0].message.content") from exc

    if not isinstance(content, str):
        raise AIClientError("OpenRouter content is not a string")
    return content


def _fallback_summary(context: dict[str, Any]) -> str:
    scenario = str(context.get("scenario") or "разбор").strip()
    cards = [str(item).strip() for item in context.get("cards", []) if str(item).strip()]
    prompts = [str(item).strip() for item in context.get("prompts", []) if str(item).strip()]
    focus = str(context.get("focus") or "").strip()

    fragments: list[str] = []
    if cards:
        fragments.append(f"Сейчас можно опереться на образы {', '.join(cards[:3])}.")
    if focus:
        fragments.append(f"Фокус этого шага — {focus}.")
    elif prompts:
        fragments.append(f"Полезно задержаться на вопросе: {prompts[0]}")
    else:
        fragments.append(f"В этом сценарии важно заметить, что особенно отзывается тебе в {scenario}.")
    return " ".join(fragments)


def _fallback_small_step(context: dict[str, Any]) -> str:
    scenario = str(context.get("scenario") or "разборе").strip()
    prompts = [str(item).strip() for item in context.get("prompts", []) if str(item).strip()]
    focus = str(context.get("focus") or "").strip()

    if focus:
        return f"Выдели 5 минут и запиши одну короткую мысль про {focus}."
    if prompts:
        return f"Запиши 1-2 предложения в ответ на вопрос: {prompts[0]}"
    return f"Сделай паузу на 2 минуты и отметь, что в этом {scenario} кажется самым важным."
