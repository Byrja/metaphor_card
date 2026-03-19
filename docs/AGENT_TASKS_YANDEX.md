# AGENT TASKS — YANDEX

## Scope
UX, copywriting, prompts, safety wording, content quality.

## Current tasks

### Y-01 UX v4 final fix
- Довести `UX_PATCH_MAP_PYTHON_v4.json` до валидного состояния.
- Убрать no-op replacements (`old == new`).
- Убрать битую кодировку в yaml/json/md.

**DoD:** `make ux-v4-check` green, нет `�`.

### Y-02 Conversational quality polish
- Улучшить `/situation` и error/safety microcopy:
  - меньше шаблонности,
  - мягкая конкретика,
  - без директивности.

**DoD:** минимум 8 meaningful replacements в v4-map.

### Y-03 Card metadata pack
- Подготовить metadata для Style-C карт:
  - card code
  - title_ru
  - tags
  - short meaning
  - prompt seed key

**DoD:** готов yaml/json, пригодный для runtime.

## Reporting format
```
TASK: <id>
RESULT: <1-3 строки>
FILES: <пути>
PROOF: <commit/hash/log>
CHECKS: <ux-v4-check + дополнительные>
RISKS: <если есть>
NEXT: <следующий шаг>
```
