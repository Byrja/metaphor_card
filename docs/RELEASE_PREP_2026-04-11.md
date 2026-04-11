# Release Prep — 2026-04-11 (metaphor_card)

## Scope
Pre-merge hardening and repo hygiene before merging feature branch into `main`.

## Done
- ✅ Smoke script fixed to be python3/venv-aware (`scripts/smoke.sh`)
- ✅ Smoke run passed end-to-end on host
- ✅ Runtime artifacts ignored in git (`data/`, `state/`, sqlite patterns)

## Current branch
- `codex/update-agent_tasks_codex-and-agent_execution_board-documents`

## Release gate checklist
- [x] Unit tests green (`pytest`)
- [x] Smoke script green (`./scripts/smoke.sh`)
- [x] No accidental runtime artifacts staged
- [ ] Confirm merge target and strategy (`main`, fast-forward or PR merge)
- [ ] Create release note summary for Sasha

## Merge plan
1. `git fetch origin`
2. Rebase branch on latest `origin/main`
3. Re-run `pytest` and `./scripts/smoke.sh`
4. Merge to `main`
5. Push `main`
6. Restart `byr-shizabot.service` and verify `active`

## Rollback
- Keep previous known-good main commit hash before merge
- If regression appears: `git checkout <prev>` + service restart
