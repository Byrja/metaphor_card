# AGENT TASKS — CODEX

## Scope
Runtime, integration, tests, deployment reliability.

## Current tasks

### C-01 Inline UX stability
- Проверить inline-кнопки и callback flow (`/start`, day/checkin/situation/history/patterns/nudge).
- Исправить runtime ошибки callback/import/typing.

**DoD:** все кнопки отвечают, fallback корректный.

### C-02 Polling reliability
- Single-instance guard, исключить 409 conflicts.
- Обновить runbook по безопасному рестарту.

**DoD:** нет регулярных 409 при штатном запуске.

### C-03 Cards pipeline hardening
- `make cards-check` green по умолчанию.
- `make cards-prepare-approved` green.
- Синхрон draft/manifest при обновлениях.

**DoD:** pytest/smoke/cards-check/cards-prepare-approved — green.

### C-04 AI integration scaffold (hybrid)
- OpenRouter-ready client в отдельном модуле:
  - `summarize_reflection(context)`
  - `next_small_step(context)`
- fallback rule-based при недоступности AI.
- вызов AI только в конце сценариев.

**DoD:** feature-flag AI + обратная совместимость.

## Reporting format
```
TASK: <id>
RESULT: <1-3 строки>
FILES: <пути>
PROOF: <commit/hash/log>
CHECKS: <pytest/smoke/make>
RISKS: <если есть>
NEXT: <следующий шаг>
```
