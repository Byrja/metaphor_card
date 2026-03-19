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
   # optional: override if you want the lock outside DATABASE_PATH directory
   # POLLING_LOCK_PATH=/var/lock/metaphor_card/polling.lock
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

Безопасный ручной рестарт вне `systemd` делай только после завершения предыдущего процесса и с тем же lock-path:
```bash
cd /opt/metaphor_card
POLLING_LOCK_PATH=/var/lock/metaphor_card/polling.lock .venv/bin/python -m app.main
```
Если lock уже занят, `app.main` завершится с кодом `3` и сообщением `Polling lock error`, не создавая второй long-polling процесс.

## 4. Проверка single-instance
Пока сервис запущен, повторный `ExecStart` с тем же lock-файлом завершится сразу и не создаст второй polling-процесс. Это убирает типичный источник `409 Conflict` для Telegram long polling.

Проверка вручную:
```bash
sudo -u metaphor /usr/bin/flock -n /var/lock/metaphor_card/polling.lock /bin/true && echo unlocked || echo locked
```

Дополнительно можно проверить runtime-guard самого приложения: пока бот запущен, повторный `python -m app.main` с тем же `POLLING_LOCK_PATH` завершится без запуска polling. Это полезно при ручных smoke/restart-сценариях и защищает даже вне `systemd`.

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

## 6. Как интегрировать UX-пак от Yandex безопасно
1. Подготовить approved-артефакты в `docs/ux-pack-v3-python/approved/` и обновить `docs/ux-pack-v3-python/manifest.json`. Каждый файл в manifest обязан указывать только целевые пути под `content/` или `docs/` — это страховка от случайного изменения runtime-кода.
2. Прогнать валидацию пакета:
   ```bash
   make ux-check
   ```
   Проверка падает, если не хватает обязательных файлов, найдены placeholders (`TODO`, `{{...}}`, `<...>`), символ `�` или сломан `yaml/json`.
3. Посмотреть dry-run diff перед копированием:
   ```bash
   ./scripts/integrate_yandex_ux.sh
   ```
4. Применить approved UX-артефакты только после чистого diff/ревью:
   ```bash
   ./scripts/integrate_yandex_ux.sh --apply
   ```
5. Сразу после интеграции выполнить smoke-прогон:
   ```bash
   PYTHONPATH=src:. ./scripts/smoke.sh
   ```
6. Для PR приложить proof-блок: output `make ux-check`, output интеграционного dry-run/apply и список изменённых файлов (`git status --short`).

## 7. Smoke после деплоя
После каждого выката:
```bash
cd /opt/metaphor_card
PYTHONPATH=src:. ./scripts/smoke.sh
```

Ожидаемый результат:
- `/start` проходит;
- сценарии `/checkin` и `/situation` проходят без исключений;
- smoke проверяет один UX v4 текст в `/checkin`;
- smoke проверяет один UX v4 текст в `/situation`;
- smoke проверяет один safety/error microcopy-текст из UX v4;
- smoke завершает процесс корректно.

## 8. Если сервис не поднялся
1. Проверить конфиг:
   ```bash
   sudo systemctl status metaphor-card.service
   journalctl -u metaphor-card.service -n 50 --no-pager
   ```
2. Проверить `.env` и валидность `BOT_TOKEN`.
3. Проверить права на `DATABASE_PATH` и lock-директорию.
4. Проверить наличие контента в `CONTENT_ROOT`.
5. Если контент недоступен, бот запустится на fallback-контенте — это допустимый degraded mode, но не финальное production-состояние.
