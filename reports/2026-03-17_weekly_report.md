# Weekly Pilot Report — 2026-03-17

## What was done
- Поднят и расширен MVP runtime бота (`/start`, `/day`, `/checkin`, `/situation`, `/insight`, `/history`, `/patterns`, `/nudge`).
- Подключены контент-паки из `content/` (decks + prompts).
- Реализованы safety guardrails (rule-based medium/high).
- Добавлен memory engine v1: повторяющиеся темы + мягкие подсказки.

## Early observations (qualitative)
- Пользовательский путь «карта → инсайт → история» уже цельный.
- Сценарий `/patterns` + `/nudge` даёт ощущение персонализации.
- Rule-based safety требует дальнейшей калибровки словарей (риск false positives).

## Risks
1. Нет телеметрии production-уровня (метрики пока описаны, но не собраны автоматически).
2. Контент selection пока без полноценного crisis-aware фильтра в runtime.
3. Нужны unit/integration тесты поверх memory/safety модулей.

## Next week focus
1. Добавить structured event logging для KPI из `docs/METRICS.md`.
2. Включить фильтрацию карт по crisis-mode ограничениям из taxonomy.
3. Подготовить `docs/QA_CHECKLIST.md` прогон как формальный pre-release gate.
