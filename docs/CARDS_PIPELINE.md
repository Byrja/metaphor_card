# Cards pipeline for `assets/cards/style-c`

## Что хранится в пайплайне

- `assets/cards/style-c/drafts/` — исходные изображения от художника или из импорта.
- `assets/cards/style-c/manifest.yaml` — единый реестр карточек со статусами `draft` и `approved`.
- `assets/cards/style-c/processed/` — подготовленные файлы для рантайма бота.
- `assets/cards/style-c/thumbs/` — миниатюры для ревью и будущих админ-интерфейсов.

## Как добавить новую картинку

1. Скопируйте исходник в `assets/cards/style-c/drafts/`.
2. Добавьте запись в `assets/cards/style-c/manifest.yaml` с полями:
   - `id` — стабильный идентификатор;
   - `slug` — машинное имя карточки;
   - `title_ru` — человекочитаемое название;
   - `tags` — список тегов;
   - `source_file` — относительный путь до файла в `drafts/`;
   - `processed_file` — относительный путь до итогового WEBP в `processed/`;
   - `status` — `draft` или `approved`.
3. Запустите проверку:

   ```bash
   make cards-check
   ```

Проверка валидирует наличие файла, допустимое расширение, дубликаты `id`/`slug`, соответствие aspect ratio к 3:4 и конфликты имён в `processed_file`.

## Как перевести карточку из `draft` в `approved`

1. Убедитесь, что `slug` совпадает с кодом карточки, которую бот должен использовать в контенте.
2. Обновите `status: approved` в `assets/cards/style-c/manifest.yaml`.
3. При необходимости скорректируйте `processed_file`, чтобы итоговый путь был уникальным.
4. Подготовьте только approved-карточки:

   ```bash
   make cards-prepare-approved
   ```

После этого `app.content.ContentService` подхватит `processed_file` для approved-записей из manifest. Если manifest отсутствует или не проходит валидацию, бот продолжает работать на текущих `image_uri` из YAML-колод.

## Как прогнать checks/prepare

### Полная валидация

```bash
make cards-check
```

### Подготовка всех записей

```bash
make cards-prepare
```

### Подготовка только approved

```bash
make cards-prepare-approved
```

### Dry-run без записи файлов

```bash
python scripts/cards_prepare.py --dry-run --only approved
```

## Технические детали

- Целевой размер основной карточки: `1536x2048`.
- Целевой размер миниатюры: `384x512`.
- При наличии Pillow скрипт делает реальную нормализацию и сохраняет WEBP.
- В средах без Pillow скрипт использует безопасный fallback без ресайза, чтобы CI и smoke-проверки не ломались; это подходит для тестов, но для продакшен-подготовки рекомендуется запускать pipeline с Pillow.
