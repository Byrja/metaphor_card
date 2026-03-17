# SERVICE_CONTRACTS.md

## 1. Scope
Контракты внутренних сервисов MVP:
- Card Selection Service
- Dialogue Orchestration Service
- Memory/Pattern Service
- Safety Guard Service

---

## 2. Card Selection Service

## 2.1 Method
`select_cards(scenario_type, user_id, count, safety_mode) -> Card[]`

## 2.2 Input
- `scenario_type`: `day_card | check_in | situation_review`
- `user_id`: integer
- `count`: integer (1..5)
- `safety_mode`: `normal | conservative`

## 2.3 Output
Массив карт:
- `card_id`
- `code`
- `title`
- `image_uri`
- `tags[]`

## 2.4 Rules
- Только `is_active = true`.
- В `conservative` режиме исключать high-intensity карты.
- Для `situation_review` возвращать неповторяющиеся карты.

---

## 3. Dialogue Orchestration Service

## 3.1 Method
`next_bot_action(session_id, user_message) -> BotAction`

## 3.2 Input
- `session_id`
- `user_message` (может быть `null` в начале)

## 3.3 Output (BotAction)
- `action_type`: `send_text | send_card | send_buttons | close_session | escalate_safety`
- `text`
- `cards[]`
- `buttons[]`
- `state_patch` (изменения state machine)

## 3.4 Guarantees
- Следует stage-последовательности из `SESSION_FLOW.md`.
- Не выдаёт авторитарные интерпретации карты.
- Всегда имеет безопасный выход (`pause/finish`) на этапах L2+.

---

## 4. Memory/Pattern Service

## 4.1 Methods
1. `save_insight(session_id, user_id, insight_text, small_step_text, emotion_tags[])`
2. `get_recent_history(user_id, limit)`
3. `detect_patterns(user_id) -> Pattern[]`

## 4.2 Output shapes
### HistoryItem
- `session_id`
- `scenario_type`
- `insight_text`
- `small_step_text`
- `created_at`

### Pattern
- `pattern_key`
- `score`
- `last_seen_at`

---

## 5. Safety Guard Service

## 5.1 Method
`assess_message_risk(user_id, session_id, text) -> SafetyDecision`

## 5.2 Output (SafetyDecision)
- `risk_level`: `low | medium | high`
- `triggered_rules[]`
- `requires_escalation`: boolean
- `safe_reply_template_code`

## 5.3 Runtime behavior
- `high`: немедленный `escalate_safety`, остановка карточного флоу.
- `medium`: укороченный сценарий + рекомендация живой помощи.
- `low`: продолжение текущей сессии.

---

## 6. Error contracts
Единый формат ошибок:
```json
{
  "error_code": "SERVICE_UNAVAILABLE",
  "message": "Human-readable short message",
  "retryable": true
}
```

Коды:
- `INVALID_INPUT`
- `NOT_FOUND`
- `STATE_CONFLICT`
- `SERVICE_UNAVAILABLE`

---

## 7. Observability contracts
Каждый сервис обязан логировать:
- `event_name`
- `user_id` (если есть)
- `session_id` (если есть)
- `latency_ms`
- `result` (`ok`/`error`)
- `error_code` (если есть)
