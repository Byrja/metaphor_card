# DEPLOY_RUNBOOK.md

## Цель
Минимальный runbook для production-развёртывания Metaphor Card как `systemd`-сервиса с single-instance защитой, рестарт-политикой и понятной диагностикой.

## 1. Подготовка сервера
1. Создать системного пользователя:
   ```bash
   sudo useradd --system --create-home --shell /bin/bash metaphor
   ```
2. Развернуть код, например в `/opt/metaphor_card`.
3. Подготовить venv:
   ```bash
   cd /opt/metaphor_card
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Создать `.env`:
   ```dotenv
   BOT_TOKEN=<real_token>
   APP_ENV=prod
   DATABASE_PATH=/var/lib/metaphor_card/metaphor_card.db
   CONTENT_ROOT=/opt/metaphor_card/content
   LOG_LEVEL=INFO
   ```
5. Подготовить директории данных и lock-файл:
   ```bash
   sudo mkdir -p /var/lib/metaphor_card /var/lock/metaphor_card
   sudo chown -R metaphor:metaphor /var/lib/metaphor_card /var/lock/metaphor_card /opt/metaphor_card
   ```

## 2. systemd unit
Файл: `/etc/systemd/system/metaphor-card.service`

```ini
[Unit]
Description=Metaphor Card Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=metaphor
Group=metaphor
WorkingDirectory=/opt/metaphor_card
EnvironmentFile=/opt/metaphor_card/.env

# single-instance guard: второй процесс не стартует, пока lock занят
ExecStart=/usr/bin/flock -n /var/lock/metaphor_card/polling.lock /opt/metaphor_card/.venv/bin/python -m app.main

Restart=on-failure
RestartSec=5s
TimeoutStartSec=30
TimeoutStopSec=20
KillSignal=SIGINT

# journald logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=metaphor-card

# filesystem hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/lib/metaphor_card /var/lock/metaphor_card /opt/metaphor_card

[Install]
WantedBy=multi-user.target
```

## 3. Запуск и управление
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now metaphor-card.service
sudo systemctl status metaphor-card.service
```

Остановить / перезапустить:
```bash
sudo systemctl stop metaphor-card.service
sudo systemctl restart metaphor-card.service
```

## 4. Проверка single-instance
Пока сервис запущен, повторный `ExecStart` с тем же lock-файлом завершится сразу и не создаст второй polling-процесс. Это убирает типичный источник `409 Conflict` для Telegram long polling.

Проверка вручную:
```bash
sudo -u metaphor /usr/bin/flock -n /var/lock/metaphor_card/polling.lock /bin/true && echo unlocked || echo locked
```

## 5. Логи и ротация
Основной режим — `journald`.

Полезные команды:
```bash
journalctl -u metaphor-card.service -n 100 --no-pager
journalctl -u metaphor-card.service -f
```

Если нужна файловая ротация, перенаправляйте stdout/stderr отдельным wrapper-скриптом и добавьте `logrotate`, например:
```conf
/var/log/metaphor-card/*.log {
  daily
  rotate 7
  compress
  missingok
  notifempty
  copytruncate
}
```

## 6. Smoke после деплоя
После каждого выката:
```bash
cd /opt/metaphor_card
PYTHONPATH=src:. ./scripts/smoke.sh
```

Ожидаемый результат:
- `/start` проходит;
- один сценарий проходит без исключений;
- smoke проверяет один UX v3 текст в `/checkin`;
- smoke завершает процесс корректно.

## 6.1 Apply UX v3
Перед применением UX v3-карты проверь guard на целевой JSON:

```bash
cd /opt/metaphor_card
make ux-v3-check
```

Для dry-run пайплайна используй тот же v3 map через apply-gate:

```bash
cd /opt/metaphor_card
make ux-v3-dry
```

Если guard прошёл, запускай apply-этап:

```bash
cd /opt/metaphor_card
make ux-v3-apply
```

По умолчанию все три команды читают `docs/UX_PATCH_MAP_PYTHON_v3.json`. Guard завершится с ошибкой, если:
- `items` пустой;
- `source` содержит placeholder-маркер;
- любой `old_snippet` совпадает с `new_snippet`.

## 7. Если сервис не поднялся
1. Проверить конфиг:
   ```bash
   sudo systemctl status metaphor-card.service
   journalctl -u metaphor-card.service -n 50 --no-pager
   ```
2. Проверить `.env` и валидность `BOT_TOKEN`.
3. Проверить права на `DATABASE_PATH` и lock-директорию.
4. Проверить наличие контента в `CONTENT_ROOT`.
5. Если контент недоступен, бот запустится на fallback-контенте — это допустимый degraded mode, но не финальное production-состояние.

## 8. Yandex UX v3 intake checklist
Перед интеграцией нового UX-пакета прогоняйте короткий intake-checklist:

1. Убедиться, что входной pack root — `docs/ux-pack-v3-python`.
2. Проверить наличие `docs/UX_PATCH_MAP_PYTHON.md` внутри пакета. Если файла нет, интеграцию не запускать (`python-real-path-map required`).
3. Убедиться, что `docs/UX_PATCH_MAP_PYTHON.md` ссылается на реальные Python runtime-пути `app/*`, а не на `src/*`, `frontend/*` или абстрактные псевдонимы.
4. Проверить, что целевые пути ограничены только `content/prompts/*` и `docs/*`. Любые другие target paths должны быть отклонены до применения пакета.
5. Выполнить локально `make ux-check` и затем `make ux-apply-dry`; только после зелёного dry-run разрешать фактический `make ux-apply`.
6. После применения пакета повторно запустить `pytest` и `make smoke`, чтобы подтвердить, что UX-обновление не сломало runtime-поток.
