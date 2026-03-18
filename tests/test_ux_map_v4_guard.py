from __future__ import annotations

import json
from pathlib import Path

from scripts.ux_map_guard import run_check


def write_v4_map(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_items() -> list[dict[str, object]]:
    return [
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "SITUATION_TITLE",
            "old_snippet": "Разбор ситуации в 3 шага.",
            "new_snippet": "Посмотрим на ситуацию через 3 карты.",
            "source_key": "/situation.title",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "SITUATION_QUESTION",
            "old_snippet": "Углубляющий вопрос: {prompt}",
            "new_snippet": "Вопрос для мягкого фокуса: {prompt}",
            "source_key": "/situation.question",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "SITUATION_SAVE_HINT",
            "old_snippet": "Когда появится формулировка, сохрани её через /insight <текст>.",
            "new_snippet": "Если появится ясная формулировка, сохрани её через /insight <текст>.",
            "source_key": "/situation.save_hint",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "CHECKIN_TITLE",
            "old_snippet": "Сделаем короткий чек-ин без спешки.",
            "new_snippet": "Сделаем короткий чек-ин спокойно и без спешки.",
            "source_key": "/checkin.title",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "INSIGHT_SAVED_TEXT",
            "old_snippet": "Сохранил. Если захочешь, можно продолжить через /history, /patterns или /nudge.",
            "new_snippet": "Сохранил. Если захочешь, можно вернуться через /history, /patterns или /nudge.",
            "source_key": "/insight.saved",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "MEDIUM_RISK_REPLY",
            "old_snippet": "Похоже, сейчас правда тяжело. Давай без углубления в карты.\nПопробуй коротко заземлиться: назови 5 предметов вокруг, которые видишь, и почувствуй опору под ногами.\nЕсли напряжение не снижается, лучше связаться с живым специалистом или близким человеком прямо сейчас.",
            "new_snippet": "Похоже, сейчас и правда тяжело. Давай без углубления в карты.\nПопробуй коротко заземлиться: назови 5 предметов вокруг, которые видишь, и почувствуй опору под ногами.\nЕсли напряжение не снижается, пожалуйста, свяжись с живым специалистом или близким человеком прямо сейчас.",
            "source_key": "safety.medium",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "CRISIS_REPLY",
            "old_snippet": "Мне очень жаль, что тебе сейчас так тяжело. Оставаться с этим в одиночку не нужно.\nСейчас важнее всего твоя безопасность. Если есть риск причинить себе вред, пожалуйста, сразу обратись в экстренные службы твоей страны или к человеку, которому доверяешь.\nЕсли хочешь, начни с очень маленького шага: напиши одному человеку, что тебе нужна помощь прямо сейчас.",
            "new_snippet": "Мне очень жаль, что тебе сейчас так тяжело. Оставаться с этим в одиночку не нужно.\nСейчас важнее всего твоя безопасность. Если есть риск причинить себе вред, пожалуйста, сразу обратись в экстренные службы твоей страны или к человеку, которому доверяешь.\nЕсли можешь, начни с очень маленького шага: напиши одному человеку, что тебе нужна помощь прямо сейчас.",
            "source_key": "safety.high",
        },
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "UNKNOWN_COMMAND_TEXT",
            "old_snippet": "Я пока лучше всего понимаю команды. Если хочешь начать, напиши /start.",
            "new_snippet": "Я пока лучше всего понимаю команды. Если хочешь, начни с /start.",
            "source_key": "fallback.unknown_command",
        },
    ]


def test_run_check_accepts_valid_v4_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v4.json"
    write_v4_map(
        map_path,
        {"version": "4", "source": "runner export 2026-03-18T12:00:00Z", "items": valid_items()},
    )

    assert run_check(map_path) == 0


def test_run_check_fails_for_too_few_v4_items(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v4.json"
    write_v4_map(
        map_path,
        {"version": "4", "source": "runner export 2026-03-18T12:00:00Z", "items": valid_items()[:7]},
    )

    assert run_check(map_path) == 1


def test_run_check_fails_for_duplicate_old_snippet_pair(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v4.json"
    items = valid_items()
    items[-1] = {
        "target_file": "app/ux_copy.py",
        "target_symbol": "ALIAS_UNKNOWN_COMMAND_TEXT",
        "old_snippet": items[0]["old_snippet"],
        "new_snippet": "Новый текст без дубликата.",
        "source_key": "fallback.alias",
    }
    write_v4_map(
        map_path,
        {"version": "4", "source": "runner export 2026-03-18T12:00:00Z", "items": items},
    )

    assert run_check(map_path) == 1


def test_run_check_fails_for_malformed_root(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v4.json"
    write_v4_map(map_path, ["version", "4"])

    assert run_check(map_path) == 1
