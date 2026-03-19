# AGENT EXECUTION BOARD — metaphor_card

Единый файл задач для параллельной работы агентов.

## Source of truth
- Repo: `https://github.com/Byrja/metaphor_card`
- Branch strategy:
  - `main` — production baseline
  - `codex/*` — runtime/integration/tests
  - `yandex/*` (или внешнее SourceCraft) — UX/copy/content

## Working model (mandatory)
1. Один task = один commit/PR.
2. Никаких «готово» без proof.
3. Merge только после:
   - tests green
   - smoke green
   - no regressions
4. Не коммитить runtime артефакты (`.venv`, `bot-run.log`, `bot-run.pid`).

---

## CURRENT SPRINT GOAL (48h)
Собрать стабильный MVP с приятным UX и картами Style-C + гибридный AI summary.

---

## TRACK A — CODEX (runtime/quality/integration)

### C-01 Inline UX stability
- Проверить новые inline-кнопки и callback flow (`/start`, day/checkin/situation/history/patterns/nudge).
- Исправить любые runtime ошибки callback/typing/import.

**DoD:**
- `/start` показывает меню кнопок
- все кнопки отвечают
- fallback корректный

### C-02 Polling reliability
- Single-instance guard для polling (исключить 409 conflicts).
- Док в runbook: как безопасно рестартить.

**DoD:**
- нет регулярных 409 в логах при штатном запуске

### C-03 Cards pipeline hardening
- Поддерживать `make cards-check` = green без ручных танцев.
- Поддерживать `make cards-prepare-approved` = green.
- Синхрон draft/manifest при обновлениях.

**DoD:**
- `cards-check`, `cards-prepare-approved`, `pytest`, `smoke` green

### C-04 AI integration scaffold (hybrid)
- Добавить провайдер-клиент (OpenRouter-ready) в отдельный модуль:
  - `summarize_reflection(context)`
  - `next_small_step(context)`
- Добавить fallback rule-based при недоступности AI.
- Вызов AI только в конце сценариев (cost-safe).

**DoD:**
- фича-флаг AI
- при выключенном AI всё работает как раньше

---

## TRACK B — YANDEX (UX/copy/content)

### Y-01 UX v4 final fix
- Довести `UX_PATCH_MAP_PYTHON_v4.json` до валидного состояния.
- Убрать no-op replacements (`old == new`).
- Убрать битую кодировку в yaml/json/md.

**DoD:**
- `make ux-v4-check` green
- нет символа `�` в изменённых файлах

### Y-02 Conversational quality polish
- Улучшить тексты в `/situation` и error/safety microcopy:
  - меньше шаблонности
  - мягкая конкретика
  - без директивности

**DoD:**
- минимум 8 meaningful replacements в v4-map
- в changelog указаны before/after примеры

### Y-03 Card content metadata
- Подготовить metadata для уже сгенерённых Style-C карт:
  - card code
  - title_ru
  - tags
  - short meaning
  - prompt seed key

**DoD:**
- готов yaml/json, пригодный для runtime контента

---

## ART TRACK (owner-driven, with assistant import)
- Генерация карт идёт отдельно.
- Все присланные в чат карты импортируются в:
  - `assets/cards/style-c/drafts/`
  - `assets/cards/style-c/INDEX.md`

---

## Acceptance gates before "MVP test now"
1) `pytest` green
2) `scripts/smoke.sh` green
3) `make cards-check` green
4) `/start` с inline-кнопками работает
5) `ux-v4-check` green

---

## Reporting format (mandatory)
Каждый агент завершает задачу в формате:

```
TASK: <id>
RESULT: <1-3 строки>
FILES: <пути>
PROOF: <commit/hash/log>
CHECKS: <pytest/smoke/make targets>
RISKS: <если есть>
NEXT: <следующий шаг>
```

---

## Quick commands (local)
```bash
pytest -q
PYTHONPATH=/srv/openclaw-bus/metaphor_card:/srv/openclaw-bus/metaphor_card/src scripts/smoke.sh
make cards-check
make cards-prepare-approved
make ux-v4-check
```
