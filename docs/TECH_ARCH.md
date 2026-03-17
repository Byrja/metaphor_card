# TECH_ARCH — техническая архитектура MVP

## 1. Выбранный стек
- **Язык:** Python 3.12+
- **Telegram framework:** aiogram 3.x
- **Хранение данных (MVP):** SQLite (с переходом на Postgres без изменения схемы)
- **Миграции:** SQL-файлы в `migrations/`
- **Конфигурация:** `.env` + pydantic-settings
- **Логирование:** встроенный `logging` (JSON-friendly формат позже)

## 2. Компоненты приложения
1. **Bot interface layer** (`src/metaphor_bot/bot.py`)
   - обработка команд `/start`, `/day_card`, `/check_in`, `/situation`, `/save_insight`, `/history`, `/patterns`, `/metrics`, `/admin_metrics`
   - отправка текстовых сообщений пользователю
2. **Dialogue layer** (`src/metaphor_bot/flows.py`)
   - сценарии: onboarding, карта дня, check-in, разбор ситуации
   - генерация открытых вопросов
3. **Domain/content layer** (`src/metaphor_bot/cards.py`)
   - каталог карт (MVP: in-memory)
   - выбор карты для пользователя
4. **Persistence layer** (`src/metaphor_bot/db.py`, `src/metaphor_bot/repository.py`)
   - users / sessions / session_messages / insights / safety_events
   - CRUD-операции + история инсайтов + персистентное состояние активных flow
5. **Safety guard layer** (`src/metaphor_bot/safety.py`)
   - red-flag детекция по ключевым фразам
   - переключение на безопасный ответ

## 3. Поток запроса (пример: /day_card)
1. Пользователь вызывает команду.
2. Flow стартует сессию в БД.
3. Сервис карт выбирает карту.
4. Бот отправляет описание карты + вопрос L1.
5. Ответ пользователя проходит safety-проверку.
6. При нормальном сценарии — L2/L4, затем сохранение инсайта.
7. При red flags — emergency response и лог safety-события.

## 4. Хранение медиа карт
- В MVP карты представлены текстовыми метафорами.
- Следующий шаг: хранить изображения в `assets/cards/` или S3-совместимом хранилище.
- В БД хранить `image_path`/`image_url`.

## 5. Observability
- Логируем события:
  - `session_started`
  - `session_completed`
  - `insight_saved`
  - `safety_triggered`
  - `flow_resumed_after_restart` (план)
- Минимальные метрики считаются SQL-запросами из БД и доступны пользователю через `/metrics`, а агрегаты продукта — через `/admin_metrics [days]` (роль admin, включая breakdown по сценариям).

## 6. Масштабирование после MVP
- Переключение SQLite → Postgres.
- Вынос safety/диалог-движка в отдельные сервисы.
- Добавление очереди задач для аналитики и рассылок.
