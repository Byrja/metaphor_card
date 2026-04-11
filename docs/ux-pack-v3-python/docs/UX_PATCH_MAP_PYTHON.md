# UX Patch Map v3 for Python Runtime

Этот intake-пакет предназначен только для Python-репозитория и должен ссылаться на реальные runtime-пути `app/*`.

## Runtime mapping
- `app/bot.py` — точка входа для пользовательских сценариев и видимых текстов.
- `app/content.py` — загрузка prompt-layer данных и fallback-логика.
- `app/ux_copy.py` — централизованные UX-константы и тексты ответов.
- `app/safety.py` — safety wording и escalation paths.

## Allowed content targets
- `content/prompts/layers.yaml`
- `content/prompts/microcopy.yaml`
- `docs/*`

## Integration note
- Любые предложения изменить `src/*`, `frontend/*` или иные нерелевантные пути должны быть отклонены на этапе intake.
