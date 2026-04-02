# AGENT TASKS — CODEX

## Scope
Runtime, integration, tests, deployment reliability.

## Current tasks

### C-01 Inline UX reliability (P0)
- Убрать runtime-crash в callback flow.
- Проверить, что кнопки отвечают стабильно в Telegram.

**DoD:** нет падений на нажатиях, меню работает целиком.

### C-02 Session preferences (P0)
- Настройки пользователя: стиль/глубина/тон.
- Привязать настройки к генерации сессии.

**DoD:** пользователь меняет настройки и получает другой сценарий.

### C-03 Questions revamp (P0)
- Переписать вопросы под режимы (soft/balance/coach) и глубину.
- Снизить шаблонность и повысить «попадание» в состояние.

**DoD:** сценарии воспринимаются как осмысленные, не механические.

### C-04 Multi-deck readiness (P1)
- Подготовить архитектуру для разных колод.
- Добавить механизм выбора колоды.

**DoD:** новая колода подключается без изменения core-обработчиков.

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
