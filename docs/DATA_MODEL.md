# DATA_MODEL.md

## 1. Обзор
Ниже — минимальная модель данных MVP для сценариев: карта дня, чек-ин, разбор ситуации, сохранение инсайтов, история и safety-события.

---

## 2. Сущности

## 2.1 users
Пользователь Telegram.
- `id` (PK)
- `telegram_id` (UNIQUE)
- `username`
- `display_name`
- `locale`
- `created_at`
- `updated_at`

## 2.2 decks
Колоды карт.
- `id` (PK)
- `code` (UNIQUE)
- `title`
- `description`
- `is_active`
- `created_at`

## 2.3 cards
Карты внутри колоды.
- `id` (PK)
- `deck_id` (FK -> decks.id)
- `code` (UNIQUE)
- `title`
- `image_uri`
- `tags_json`
- `intensity_level` (1..5)
- `is_active`
- `created_at`

## 2.4 sessions
Сессии взаимодействия.
- `id` (PK)
- `user_id` (FK -> users.id)
- `scenario_type` (`day_card` / `check_in` / `situation_review`)
- `status` (`active` / `completed` / `aborted` / `safety_escalated`)
- `started_at`
- `completed_at`

## 2.5 session_messages
Сообщения внутри сессии.
- `id` (PK)
- `session_id` (FK -> sessions.id)
- `sender_role` (`bot` / `user` / `system`)
- `message_text`
- `stage_code` (`entry`, `l1`, `l2`, `l3`, `l4`, `closing`, `safety`)
- `created_at`

## 2.6 insights
Сохранённые выводы пользователя.
- `id` (PK)
- `session_id` (FK -> sessions.id)
- `user_id` (FK -> users.id)
- `insight_text`
- `small_step_text`
- `emotion_tags_json`
- `created_at`

## 2.7 user_patterns
Агрегаты повторяющихся тем.
- `id` (PK)
- `user_id` (FK -> users.id)
- `pattern_key`
- `pattern_value`
- `score`
- `last_seen_at`

## 2.8 safety_events
События risk-детекции.
- `id` (PK)
- `session_id` (FK -> sessions.id)
- `user_id` (FK -> users.id)
- `risk_level` (`low` / `medium` / `high`)
- `trigger_source` (`rule`, `model`, `manual`)
- `trigger_payload_json`
- `created_at`

---

## 3. Связи
- `users` 1:N `sessions`
- `decks` 1:N `cards`
- `sessions` 1:N `session_messages`
- `sessions` 1:N `insights`
- `users` 1:N `insights`
- `users` 1:N `user_patterns`
- `sessions` 1:N `safety_events`
- `users` 1:N `safety_events`

---

## 4. Индексы
- `users(telegram_id)` unique
- `sessions(user_id, started_at desc)`
- `session_messages(session_id, created_at)`
- `insights(user_id, created_at desc)`
- `safety_events(user_id, created_at desc)`
- `cards(deck_id, is_active)`

---

## 5. ERD (текст)
`users -> sessions -> session_messages`  
`users -> sessions -> insights`  
`users -> user_patterns`  
`users -> sessions -> safety_events`  
`decks -> cards`
