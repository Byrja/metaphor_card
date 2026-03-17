# Execution Plan (agents) — metaphor_card

Цель: запустить Telegram-бота метафорических карт как production-ready MVP с безопасной рефлексивной механикой.

## 0) Правила исполнения
- Каждая задача = отдельный issue/branch/PR с проверяемым артефактом.
- Никаких «готово» без proof: commit hash + demo output/screenshot + checklist.
- Безопасность и tone-of-voice — обязательные acceptance criteria, не «потом».

---

## Phase 1 — Product Foundation (P0)
**Owner:** Клава (архитектура) + Заря (контент-голос)

### 1.1 Product spec v1
**Deliverable:** `docs/PRODUCT_SPEC.md`
- ценностное предложение;
- JTBD;
- сценарии (карта дня, чек-ин, разбор ситуации, дневник);
- non-goals.

### 1.2 Tone & Safety bible
**Deliverable:** `docs/TONE_AND_SAFETY.md`
- стиль ответов (допустимые/недопустимые формулировки);
- red flags (self-harm, crisis, panic);
- fallback-сценарии и эскалация к живой помощи.

### 1.3 Session dramaturgy
**Deliverable:** `docs/SESSION_FLOW.md`
- вход → карта → реакция → углубление → вывод → шаг → сохранение;
- шаблоны вопросов по слоям (L1-L4);
- критерии «сессия завершена качественно».

**DoD Phase 1:** утверждены 3 документа и baseline UX-поток.

---

## Phase 2 — Architecture & Data (P0)
**Owner:** Искра

### 2.1 Tech stack
**Deliverable:** `docs/TECH_ARCH.md`
- Telegram framework;
- storage (SQLite/Postgres);
- media storage для карт;
- observability (logs/metrics).

### 2.2 Data model
**Deliverable:** `docs/DATA_MODEL.md` + миграции
Минимум таблиц:
- users
- decks
- cards
- sessions
- session_messages
- insights
- user_patterns
- safety_events

### 2.3 API/service boundaries
**Deliverable:** `docs/SERVICE_CONTRACTS.md`
- card selection service
- dialogue orchestration service
- memory/pattern service
- safety guard service

**DoD Phase 2:** есть миграции, ERD, поднятый dev-контур.

---

## Phase 3 — Content System (P1)
**Owner:** Заря (контент) + Клава (контроль качества)

### 3.1 Card taxonomy
**Deliverable:** `content/card_taxonomy.yaml`
- темы, архетипы, эмоциональные теги;
- уровни интенсивности;
- противопоказанные сочетания в кризисном режиме.

### 3.2 Deck packs
**Deliverable:** `content/decks/*.yaml`
- base deck (MVP);
- тематические мини-колоды (отношения/работа/тревога/границы).

### 3.3 Prompt packs
**Deliverable:** `content/prompts/*.yaml`
- вопросы L1-L4;
- шаблоны итогов и «маленького шага»;
- стильные микроподводки без эзо-пафоса.

**DoD Phase 3:** контент-ядро покрывает все MVP-сценарии.

---

## Phase 4 — MVP Build (P0)
**Owner:** Искра

### 4.1 Core bot flows
**Deliverable:** working bot commands/buttons
- `/start`
- карта дня
- быстрый чек-ин
- разбор ситуации (3-карточный flow)
- сохранить инсайт
- история последних N сессий

### 4.2 Memory engine v1
**Deliverable:**
- сохранение выводов;
- поиск повторяющихся тем;
- мягкие напоминания («ты уже возвращался к этому...»).

### 4.3 Safety guardrails runtime
**Deliverable:**
- детектор кризисных маркеров;
- безопасный ответ и перенаправление к живой помощи;
- отключение «игрового» режима в risk-кейсах.

**DoD Phase 4:** end-to-end MVP с реальными сессиями и сохранением истории.

---

## Phase 5 — QA, Metrics, Iteration (P1)
**Owner:** Клава

### 5.1 Quality QA checklist
**Deliverable:** `docs/QA_CHECKLIST.md`
- нет авторитарных трактовок;
- нет токсичных/пугающих формулировок;
- сессии завершаются выводом и шагом.

### 5.2 Product metrics
**Deliverable:** `docs/METRICS.md`
- D1/D7 return rate;
- completion rate сессий;
- insight-save rate;
- повторные заходы в «разбор ситуации»;
- safety-escalation rate.

### 5.3 Pilot loop
**Deliverable:** weekly reports in `reports/`
- что не заходит;
- какие вопросы дают лучшие инсайты;
- где пользователи отваливаются.

---

## Phase 6 — Monetization Layer (после PMF)
**Owner:** Клава + Заря

- premium decks
- deep scenarios
- advanced pattern analytics
- export cards/insight snapshots
- subscription experiments

---

## Первые 10 задач для старта (сразу в работу)
1. Создать `PRODUCT_SPEC.md` (P0)
2. Создать `TONE_AND_SAFETY.md` (P0)
3. Создать `SESSION_FLOW.md` (P0)
4. Зафиксировать `TECH_ARCH.md` (P0)
5. Описать `DATA_MODEL.md` + миграции (P0)
6. Поднять skeleton-бота с `/start` и «карта дня» (P0)
7. Добавить flow «быстрый чек-ин» (P0)
8. Добавить flow «разбор ситуации 3 карты» (P0)
9. Реализовать сохранение инсайта + просмотр истории (P0)
10. Включить safety-guard runtime (P0)

---

## Формат отчётности агентов
Каждый шаг закрывается сообщением:
- Что сделано
- Где (файлы/коммит)
- Как проверено
- Риски/что дальше

Шаблон:
```
TASK: <id>
RESULT: <1-3 строки>
FILES: <пути>
PROOF: <commit/hash/log/screenshot>
RISKS: <если есть>
NEXT: <следующий шаг>
```
