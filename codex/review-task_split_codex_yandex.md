# review-task_split_codex_yandex

## Short changelog
- added deployment runbook with `systemd`, `flock` single-instance guard, restart policy, and log strategy
- added offline smoke script covering `/start`, one scenario (`/checkin`), and graceful shutdown
- extracted UX copy into runtime-safe constants and refreshed visible texts without changing polling architecture
- added merge-ready Yandex UX artifacts: text guide, button map, session copybook, safety UX pack, and patch map
- kept runtime compatible with current slash-command flow to avoid regressions before keyboard rollout
