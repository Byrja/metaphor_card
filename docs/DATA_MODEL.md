# DATA_MODEL — минимальная модель данных MVP

## 1. Сущности

### users
- `id` (PK)
- `telegram_id` (UNIQUE)
- `username`
- `first_name`
- `created_at`

### sessions
- `id` (PK)
- `user_id` (FK -> users.id)
- `scenario` (`day_card`, `check_in`, `situation`)
- `status` (`active`, `completed`, `aborted`, `safety_interrupted`)
- `started_at`
- `completed_at`

### session_messages
- `id` (PK)
- `session_id` (FK -> sessions.id)
- `role` (`bot`, `user`, `system`)
- `message_text`
- `created_at`

### insights
- `id` (PK)
- `session_id` (FK -> sessions.id)
- `user_id` (FK -> users.id)
- `insight_text`
- `next_step`
- `created_at`

### cards
- `id` (PK)
- `code` (UNIQUE)
- `title`
- `prompt`
- `theme`
- `intensity`

### safety_events
- `id` (PK)
- `user_id` (FK -> users.id)
- `session_id` (FK -> sessions.id, nullable)
- `trigger_text`
- `trigger_category`
- `created_at`

### active_flows
- `id` (PK)
- `user_id` (FK -> users.id, UNIQUE)
- `session_id` (FK -> sessions.id)
- `scenario`
- `step`
- `answers_json`
- `updated_at`

## 2. Индексы
- `users(telegram_id)`
- `sessions(user_id, started_at)`
- `insights(user_id, created_at)`
- `safety_events(user_id, created_at)`
- `active_flows(user_id)`

## 3. ERD (текстом)
- Один `user` имеет много `sessions`.
- Одна `session` имеет много `session_messages`.
- Одна `session` может иметь 0..1 `insight` в MVP.
- Один `user` имеет много `insights` и `safety_events`.
- Один `user` имеет максимум один `active_flow` (текущая незавершённая сессия).

## 4. Примечания
- Таблица `cards` отделена от сессий, чтобы позже поддержать колоды.
- Для user_patterns в MVP достаточно SQL-агрегаций поверх `insights`; отдельная таблица добавится в следующей итерации.
