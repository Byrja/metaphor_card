from __future__ import annotations

import json
import socket
from unittest.mock import patch

from app import ai_client
from app.config import load_settings as real_load_settings


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _settings(**overrides: str):
    env = {
        'BOT_TOKEN': '123:abc',
        'AI_ENABLED': '1',
        'AI_PROVIDER': 'openrouter',
        'OPENROUTER_API_KEY': 'test-key',
        'OPENROUTER_MODEL': 'openai/gpt-4o-mini',
        'AI_TIMEOUT_SEC': '5',
    }
    env.update(overrides)
    return real_load_settings(env)


def test_summarize_reflection_uses_openrouter_response(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_client.request,
        'urlopen',
        lambda req, timeout=0: FakeResponse({'choices': [{'message': {'content': 'Мягкое AI-резюме.'}}]}),
    )

    text = ai_client.summarize_reflection(
        {'scenario': 'checkin', 'cards': ['Тихий маяк']},
        _settings(),
    )

    assert text == 'Мягкое AI-резюме.'


def test_suggest_small_step_falls_back_on_timeout(monkeypatch) -> None:
    def raise_timeout(req, timeout=0):
        raise socket.timeout('timed out')

    monkeypatch.setattr(ai_client.request, 'urlopen', raise_timeout)

    text = ai_client.suggest_small_step(
        {'scenario': 'checkin', 'focus': 'Тихий маяк'},
        _settings(),
    )

    assert 'Тихий маяк' in text
    assert '5 минут' in text


def test_summarize_reflection_falls_back_on_bad_response(monkeypatch) -> None:
    monkeypatch.setattr(ai_client.request, 'urlopen', lambda req, timeout=0: FakeResponse({'choices': []}))

    text = ai_client.summarize_reflection(
        {'scenario': 'situation', 'cards': ['Сад после дождя']},
        _settings(),
    )

    assert 'Сад после дождя' in text


def test_ai_client_returns_fallback_when_disabled(monkeypatch) -> None:
    with patch.object(ai_client.request, 'urlopen') as mocked:
        text = ai_client.suggest_small_step(
            {'scenario': 'checkin', 'prompts': ['Что важно?']},
            _settings(AI_ENABLED='0'),
        )

    mocked.assert_not_called()
    assert 'Что важно?' in text


def test_ai_client_uses_provided_settings_without_reloading_env(monkeypatch) -> None:
    monkeypatch.setattr(ai_client, 'load_settings', lambda: (_ for _ in ()).throw(AssertionError('should not reload env')))
    monkeypatch.setattr(
        ai_client.request,
        'urlopen',
        lambda req, timeout=0: FakeResponse({'choices': [{'message': {'content': 'short text'}}]}),
    )

    text = ai_client.summarize_reflection({'scenario': 'checkin'}, _settings())

    assert text == 'short text'
