# metaphor_card

Telegram-бот с авторскими метафорическими картами для саморефлексии (не гадание, не психотерапия).

## Документы
- `docs/PROJECT_DESCRIPTION_RU.md` — полное описание проекта (из ТЗ владельца)
- `docs/EXECUTION_PLAN_AGENTS.md` — пошаговый план выполнения для агентной команды
- `docs/PRODUCT_SPEC.md` — продуктовая спецификация v1 (ценность, JTBD, сценарии, non-goals)
- `docs/TONE_AND_SAFETY.md` — тон коммуникации и safety-правила
- `docs/SESSION_FLOW.md` — драматургия сессий и слои вопросов L1–L4
- `docs/TECH_ARCH.md` — техническая архитектура MVP
- `docs/DATA_MODEL.md` — модель данных MVP
- `docs/SERVICE_CONTRACTS.md` — контракты внутренних сервисов
- `db/migrations/0001_init.sql` — стартовая SQL-миграция
- `content/card_taxonomy.yaml` — таксономия тем/архетипов/интенсивности
- `content/decks/*.yaml` — MVP-колоды и тематические мини-колоды
- `content/prompts/*.yaml` — вопросы L1–L4, итоги и microcopy
- `docs/QA_CHECKLIST.md` — чеклист качества перед релизом
- `docs/METRICS.md` — продуктовые и safety-метрики
- `docs/DEPLOY_RUNBOOK.md` — production-runbook для systemd, single-instance и логов
- `docs/UX_TEXT_GUIDE.md`, `docs/BUTTON_MAP_MVP.md`, `docs/SESSION_COPYBOOK_MVP.md`, `docs/SAFETY_UX_MVP.md`, `docs/UX_PATCH_MAP.md` — merge-ready UX-пакет и карта интеграции текстов
- `scripts/smoke.sh` — локальный/offline smoke-check `/start` + один сценарий + graceful stop
- `reports/*.md` — еженедельные pilot-отчёты

## Текущий статус
- ✅ **Phase 1 — Product Foundation (P0)** завершена.
- 🟡 **Phase 2 — Architecture & Data (P0)** в работе (документы и стартовая миграция добавлены).
- 🟡 **Phase 3 — Content System (P1)** в работе: добавлено контент-ядро (taxonomy, decks, prompts) и подключено в runtime-сценарии.
- 🟡 **Phase 4 — MVP Build (P0)** начата: добавлен рабочий skeleton-бот с базовыми командами, SQLite-хранилищем и safety-guard runtime, memory engine v1 (повторяющиеся темы + мягкие подсказки) и crisis-aware фильтрация карт по taxonomy.
- 🟡 **Phase 5 — QA, Metrics, Iteration (P1)** начата: добавлены QA checklist, METRICS и первый weekly report.

## Локальный запуск
1. Создать venv и установить зависимости:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Скопировать `.env.example` в `.env`, заполнить `BOT_TOKEN` и при необходимости скорректировать:
   - `APP_ENV=dev` для локального режима или `APP_ENV=prod` для сервера;
   - `DATABASE_PATH` для SQLite-файла;
   - `CONTENT_ROOT`, если контент лежит вне стандартной папки `content`.
3. Запустить:
   - `python -m app.main`

Если `content/` частично недоступен, бот поднимется на встроенном минимальном fallback-контенте и продолжит core flow.
Если `LOG_LEVEL` задан некорректно, приложение автоматически использует `INFO`.

Команды бота:
- `/start`
- `/day`
- `/checkin`
- `/situation`
- `/insight <текст>`
- `/history`
- `/patterns`
- `/nudge`


## Observability (MVP)
- В runtime включен JSON event logging по модели событий из `docs/METRICS.md`.
- Ключевые события: `session_started`, `session_completed`, `insight_saved`, `patterns_opened`, `nudge_requested`, `safety_triggered`, `safety_escalated`, `content_loaded`, `db_schema_initialized`.


- В check-in используется бережный режим выбора карты (conservative) на основе `content/card_taxonomy.yaml`.