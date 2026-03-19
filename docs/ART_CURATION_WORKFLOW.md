# Art Curation Workflow (Style-C)

Пока Codex работает над runtime, заполняем метаданные карт без блокировки разработки.

## Файлы
- Draft images: `assets/cards/style-c/drafts/`
- Auto draft manifest: `assets/cards/style-c/manifest_draft.yaml`

## Как курировать
1. Проставить `title_ru`, `title_en`, `meaning_short`, `tags`.
2. Пометить финальные карты как `approved` (в отдельном production manifest).
3. Для approved карт закрепить стабильные `code` (например `mc_bridge`, `mc_mirror`).

## Критерии approved
- Символ читается за 1-2 секунды.
- Вписывается в канон стиля (рамка/палитра/свет).
- Без визуального шума и случайных артефактов.

## Минимальные теги
- emotion
- action
- theme

Пример:
- tags: ["grounding", "choice", "hope"]
