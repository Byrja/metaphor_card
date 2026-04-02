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
UX-revamp для реального использования МАК: выбор режима пользователем + улучшенные вопросы + подготовка мульти-колод.

---

## TRACK A — CODEX (runtime/quality/integration)

### C-01 Inline UX reliability (P0)
- Починить и закрепить inline flow без падений (`frozen Message`, callback-crash).
- Удалить внешние автосинк-процессы, которые откатывают runtime-фиксы.

**DoD:**
- `/start` показывает меню
- все inline-кнопки отвечают
- в логах нет повторяющегося `ValidationError ... Message.from_user`

### C-02 Session preferences (P0)
- Добавить пользовательские настройки сессии:
  - стиль: мягко / баланс / коуч
  - глубина: коротко / средне / глубоко
  - тон: дружелюбный / нейтральный / прямой
- Применять настройки к сценарию в runtime.

**DoD:**
- настройки переключаются кнопками
- сценарий реально меняет глубину/формулировки

### C-03 Questions revamp (P0)
- Переписать ядро вопросов (главная боль продукта).
- Сделать версии вопросов под 3 стиля и 3 уровня глубины.

**DoD:**
- минимум 2 тест-сценария на каждый стиль
- текст ощущается «живым», не шаблонным

### C-04 Multi-deck readiness (P1)
- Подготовить структуру для нескольких колод (базовая + тематические).
- Добавить выбор колоды в сценарии (без ломки текущего flow).

**DoD:**
- можно подключить новую колоду без правок core-логики

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
