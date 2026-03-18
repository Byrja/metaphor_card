# Точное сопоставление UX-текстов для Python-репо (v2)

## Структура Python-проекта (реальные пути)

```
metaphor_card/
├── app/
│   ├── bot.py
│   ├── content.py
│   ├── ux_copy.py
│   └── safety.py
├── content/
│   └── prompts/
│       ├── base_prompts.yaml
│       ├── daily_card.yaml
│       ├── journal.yaml
│       ├── layers.yaml
│       ├── microcopy.yaml
│       ├── quick_checkin.yaml
│       ├── situation_analysis.yaml
│       └── summaries.yaml
└── docs/
```

## Сопоставление файлов и функций (для механического применения)

### Файл: content/prompts/microcopy.yaml
#### Python-модуль: app/ux_copy.py
#### Функция: get_microcopy

##### Приветствия
- **target_file**: app/ux_copy.py
- **target_symbol**: get_microcopy
- **old_snippet**: Рад снова видеть тебя
- **new_snippet**: С возвращением! Рад видеть тебя снова
- **source_key**: content/prompts/microcopy.yaml#greetings.welcome_back

- **target_file**: app/ux_copy.py
- **target_symbol**: get_microcopy
- **old_snippet**: Доброе утро! Готов к небольшому путешествию внутрь себя?
- **new_snippet**: Доброе утро! Готов отправиться в небольшое путешествие внутрь себя?
- **source_key**: content/prompts/microcopy.yaml#greetings.good_morning

##### Ошибки
- **target_file**: app/ux_copy.py
- **target_symbol**: get_microcopy
- **old_snippet**: Кажется, что-то с загрузкой карты. Давай попробуем еще раз?
- **new_snippet**: Похоже, возникла проблема с загрузкой карты. Давай попробуем еще раз?
- **source_key**: content/prompts/microcopy.yaml#errors.card_loading

### Файл: content/prompts/layers.yaml
#### Python-модуль: app/content.py
#### Функция: get_layer_prompts

##### Уровень 1: Контакт с картой
- **target_file**: app/content.py
- **target_symbol**: get_layer_prompts
- **old_snippet**: Что первым привлекло твое внимание?
- **new_snippet**: Что первым привлекло твое внимание на этой карте?
- **source_key**: content/prompts/layers.yaml#initial_contact.questions

- **target_file**: app/content.py
- **target_symbol**: get_layer_prompts
- **old_snippet**: Какое чувство возникло?
- **new_snippet**: Какое чувство возникло у тебя при виде этой карты?
- **source_key**: content/prompts/layers.yaml#initial_contact.questions