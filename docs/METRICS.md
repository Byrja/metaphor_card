# METRICS — продуктовые и пользовательские метрики MVP

## 1. Продуктовые KPI (общий уровень)
- **Session completion rate** = completed sessions / started sessions.
- **Insight save rate** = sessions with insight / completed sessions.
- **Safety escalation rate** = safety events / total sessions.
- **Return rate (D1/D7)** — на уровне аналитики по датам активности пользователя.

## 2. Пользовательская сводка в боте (`/metrics`)
Команда `/metrics` показывает персональные показатели:
- всего сессий;
- завершённых сессий + completion rate;
- количество сохранённых инсайтов;
- количество safety-срабатываний.

Назначение: дать пользователю обратную связь о динамике практики саморефлексии.

## 3. Интерпретация
- Высокий completion rate + рост insight count обычно означает, что формат подходит пользователю.
- Рост safety events — сигнал усилить бережность и упрощать сценарии.
- Низкий completion rate — повод пересмотреть длину flow и формулировки вопросов.

## 4. Ограничения MVP
- Метрики считаются по SQLite и не агрегируются по когортам.
- Нет дашборда; анализ выполняется через SQL и команду `/metrics`.

## 5. Админские агрегаты (`/admin_metrics [days]`)
- total users;
- total sessions;
- completion rate по всем сессиям;
- total insights;
- total safety events;
- breakdown completion rate по сценариям.

Команда поддерживает опциональный период в днях: ` /admin_metrics 7 `.
Доступ ограничен списком `ADMIN_TELEGRAM_IDS` в `.env`.
