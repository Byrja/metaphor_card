# TECH_ARCH.md

## 1. Цель
Зафиксировать техническую архитектуру MVP Telegram-бота Metaphor Card для безопасных сессий саморефлексии.

---

## 2. Технологический стек (MVP)

## 2.1 Bot runtime
- **Язык:** Python 3.12
- **Фреймворк:** `aiogram` (v3)
- **Причина выбора:** зрелая экосистема, удобный FSM/routers, хорошая поддержка webhook/long-polling.

## 2.2 Backend/API
- **Web:** `FastAPI` (внутренний API и health endpoints)
- **ASGI server:** `uvicorn`
- **Причина выбора:** быстрое описание контрактов, OpenAPI, простая интеграция с async-ботом.

## 2.3 Storage
- **MVP/dev:** SQLite (локально, простая разработка)
- **Prod-ready:** PostgreSQL 16+
- **ORM/DB toolkit:** SQLAlchemy 2.x + Alembic

## 2.4 Media storage (карты)
- **MVP:** файловая директория `assets/cards/` (локально/в контейнере)
- **Prod:** S3-совместимый object storage (Yandex Object Storage / AWS S3 / MinIO)

## 2.5 Observability
- Структурированные логи в JSON (`structlog` или stdlib logging + json formatter)
- Метрики: Prometheus endpoint (`/metrics`) с ключевыми счетчиками
- Ошибки: интеграция с Sentry (prod)

---

## 3. Логическая архитектура

Компоненты:
1. **Telegram Interface Layer**
   - обработка `/start`, кнопок, пользовательских реплик;
   - маршрутизация в сценарии.
2. **Dialogue Orchestrator**
   - управление состоянием сессии;
   - выбор следующего шага (L1-L4) и шаблона ответа.
3. **Card Selection Service**
   - выбор карты/расклада по сценарию и safety-контексту.
4. **Memory & Pattern Service**
   - сохранение инсайтов и извлечение повторяющихся тем.
5. **Safety Guard Service**
   - детекция risk-маркеров;
   - переключение в кризисный протокол.
6. **Persistence Layer**
   - SQL-таблицы сессий, сообщений, инсайтов, safety-событий.

---

## 4. Deployment profile (MVP)
- Один контейнер приложения (bot + API) + БД.
- Режим запуска:
  - dev: long polling;
  - stage/prod: webhook за reverse proxy.
- Конфигурация через `.env`.

Минимальные переменные окружения:
- `BOT_TOKEN`
- `APP_ENV`
- `DATABASE_URL`
- `CARDS_STORAGE_MODE` (`local` / `s3`)
- `CARDS_STORAGE_PATH` / `S3_BUCKET`
- `SENTRY_DSN` (опционально)

---

## 5. NFR (MVP)
- P95 ответа бота < 2.5 сек без генеративных внешних вызовов.
- Доступность 99%+ на этапе пилота.
- Идемпотентная обработка Telegram update_id.
- Безопасное логирование (без чувствительных личных данных в raw-виде).

---

## 6. Technical risks
- **Риск:** ограничение SQLite при росте нагрузки.  
  **Решение:** ранняя миграция на Postgres + Alembic совместимость.
- **Риск:** высокие ложные срабатывания safety-детектора.  
  **Решение:** гибрид rule-based + ручной QA словарей.
- **Риск:** рассинхрон состояния сценария.  
  **Решение:** хранить state machine в БД + versioning состояния.
