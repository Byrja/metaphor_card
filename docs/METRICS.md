# METRICS.md

## 1. Product KPIs (MVP)

## Retention
- **D1 return rate** = users returned on day+1 / new users day0
- **D7 return rate** = users returned within 7 days / new users day0

## Funnel quality
- **Session completion rate** = completed sessions / started sessions
- **Insight-save rate** = sessions with insight / completed sessions
- **Situation re-entry rate** = users with >=2 `/situation` sessions per week / active users

## Safety
- **Safety escalation rate** = escalated sessions / all sessions
- **High-risk share** = high-risk events / all safety events
- **False-positive review rate** = manually marked false positive / all escalations

---

## 2. Operational metrics
- p95 response latency (bot message turnaround)
- DB errors per 1k requests
- content-load failures at startup
- command error rate by endpoint (`/day`, `/checkin`, `/situation`, etc.)

---

## 3. Event model (минимум)

### User events
- `session_started`
- `session_completed`
- `insight_saved`
- `history_opened`
- `patterns_opened`
- `nudge_requested`

### Safety events
- `safety_triggered` (`low|medium|high`)
- `safety_escalated`

### System events
- `content_loaded`
- `db_schema_initialized`
- `handler_error`

---

## 4. Weekly dashboard (pilot)
Каждую неделю фиксируем:
1. Active users (WAU)
2. D1/D7
3. Completion + insight-save
4. Safety escalation rate
5. Top repeating themes (aggregated)
6. Топ-3 гипотезы на улучшение

---

## 5. Target bands for pilot (ориентиры)
- D1 >= 20%
- Completion rate >= 55%
- Insight-save rate >= 45%
- Safety escalation rate: мониторим baseline, без «target to maximize/minimize» без ручной валидации

> Важно: safety метрики оцениваются вместе с ручным качественным review, чтобы не оптимизировать «вслепую».
