# Setup autosync for codex PR branches

## 1) Create token env
Create file:

`/srv/openclaw-bus/secrets/metaphor-card-sync.env`

```bash
GITHUB_TOKEN=ghp_xxx_or_fine_grained_token
```

Token scopes needed:
- Contents: Read and write
- Pull requests: Read and write (optional but useful)

## 2) Install systemd units
```bash
sudo cp /srv/openclaw-bus/metaphor_card/.ops/codex-pr-sync.service /etc/systemd/system/
sudo cp /srv/openclaw-bus/metaphor_card/.ops/codex-pr-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now codex-pr-sync.timer
```

## 3) Check status
```bash
systemctl status codex-pr-sync.timer --no-pager
journalctl -u codex-pr-sync.service -n 80 --no-pager
```

## 4) Manual run
```bash
sudo systemctl start codex-pr-sync.service
```

---

## What it does
- fetches `origin/main` and all `origin/codex/*` branches
- updates each codex branch with latest main
- auto-resolves conflicts using merge strategy `-X ours` on branch conflicts
- force-pushes updated branch (`--force-with-lease`)

Result: PRs from codex branches stay up-to-date and usually avoid GitHub conflict blocks.
