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
- сценарии `/checkin` и `/situation` проходят без исключений;
- smoke проверяет один UX v4 текст в `/checkin`;
- smoke проверяет один UX v4 текст в `/situation`;
- smoke проверяет один safety/error microcopy-текст из UX v4;
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

## 6.2 Apply UX v4 safely
Перед применением UX v4-карты сначала проверь guard на целевом JSON:

```bash
cd /opt/metaphor_card
make ux-v4-check
```

Для dry-run пайплайна используй apply-gate с тем же map:

```bash
cd /opt/metaphor_card
make ux-v4-dry
```

Если guard прошёл, запускай apply-этап:

```bash
cd /opt/metaphor_card
make ux-v4-apply
```

По умолчанию все три команды читают `docs/UX_PATCH_MAP_PYTHON_v4.json`. Для v4 guard завершится с ошибкой, если:
- root JSON не object c полями `version`, `source`, `items`;
- `items` не список;
- `items` пустой или в нём меньше 8 элементов;
- `source` содержит placeholder-маркер;
- любой `old_snippet` совпадает с `new_snippet`;
- в `items` повторяется пара `(target_file, old_snippet)`.

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


## 8. Apply Yandex UX patch-map v2
Когда от Yandex придёт `docs/UX_PATCH_MAP_PYTHON_v2.json`, его можно прогнать безопасно и воспроизводимо через integration runner.

### Что делает runner
- валидирует каждый item (`target_file`, `target_symbol`, `old_snippet`, `new_snippet`, `source_key`);
- работает в режиме all-or-nothing: сначала проверяет все замены в памяти, и только потом пишет файлы;
- падает, если `old_snippet` не найден, найден больше одного раза или совпадает с `new_snippet`;
- всегда создаёт отчёт `reports/ux_patch_apply_report.json`.

### Команды
Проверить, что map корректен и все замены однозначны:
```bash
make ux-map-check
```

Посмотреть diff и отчёт без изменения файлов:
```bash
make ux-map-dry
```

Применить patch-map:
```bash
make ux-map-apply
```

Эквивалентный прямой запуск:
```bash
python3 scripts/apply_ux_patch_map.py --map docs/UX_PATCH_MAP_PYTHON_v2.json --dry-run
python3 scripts/apply_ux_patch_map.py --map docs/UX_PATCH_MAP_PYTHON_v2.json --apply
```

### Что проверять перед merge/apply
1. `pytest -q tests/test_apply_ux_patch_map.py` — unit coverage для success / not found / duplicate / no-op.
2. `make ux-map-dry` — dry-run должен завершаться успешно и сформировать report.
3. `reports/ux_patch_apply_report.json` — в отчёте должны быть `ok`, `summary`, `items`, `errors`.
4. Если dry-run упал, не запускать `ux-map-apply`, пока не исправлены target snippets или сам map.

### Примечание про placeholder map
В репозитории лежит placeholder `docs/UX_PATCH_MAP_PYTHON_v2.json` с пустым `items`, чтобы CI/локальные команды были готовы заранее. После прихода финального файла от Yandex замените содержимое JSON и повторите `make ux-map-dry`.
