# MVP Live Test Checklist (5–10 min)

Цель: быстро понять, что бот готов к ручному тесту без глубокого дебага.

## 0) Smoke precheck (operator)
```bash
pytest -q
PYTHONPATH=/srv/openclaw-bus/metaphor_card:/srv/openclaw-bus/metaphor_card/src scripts/smoke.sh
make cards-check
make cards-prepare-approved
make ux-v4-check
```
Ожидание: все команды green.

---

## 1) Telegram UX check (owner)

### 1.1 Старт
- Отправить `/start`
- Проверить:
  - есть приветствие с инструкцией
  - есть inline-кнопки меню

### 1.2 Кнопки меню
Нажать по очереди:
- 🃏 Карта дня
- 🫶 Чек-ин
- 🔎 Разбор ситуации
- 🧠 Паттерны
- 📚 История
- ✨ Мягкая подсказка

Ожидание:
- каждая кнопка отвечает
- после ответа меню остаётся/возвращается
- нет сообщений об ошибке

### 1.3 Insight flow
- После `/day` или `/situation` отправить:
  - `/insight Сегодня мне важно замедлиться и выбрать один шаг`
- Проверить:
  - подтверждение сохранения
- Затем `/history`:
  - инсайт виден в списке

### 1.4 Safety check
- Отправить тестовую фразу риска в `/insight`:
  - `/insight у меня паника и мне очень страшно`
- Ожидание:
  - приходит safety-ответ
  - без агрессии и без "медицинских обещаний"

---

## 2) Cards check
- Убедиться, что карточные ответы приходят стабильно
- Нет падений из-за manifest/draft mismatch

---

## 3) Pass/Fail rubric

## PASS
- все разделы 1.1–1.4 успешно
- нет ошибок в логах уровня crash

## SOFT FAIL
- UX шероховатости (формулировки/кнопки) при рабочем core

## HARD FAIL
- не работает /start
- не отвечают кнопки
- падает /insight
- safety не срабатывает

---

## 4) Report format (после живого теста)
```text
LIVE_TEST:
START: ok/fail
MENU_BUTTONS: ok/fail
INSIGHT_SAVE: ok/fail
HISTORY: ok/fail
SAFETY: ok/fail
NOTES: <коротко>
```
