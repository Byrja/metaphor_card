#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/srv/openclaw-bus/metaphor_card}"
cd "$REPO_DIR"

# Optional token auth (recommended via env file/systemd)
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/Byrja/metaphor_card.git"
fi

git fetch origin --prune

MAIN_REF="origin/main"

mapfile -t BRANCHES < <(git for-each-ref --format='%(refname:short)' refs/remotes/origin/codex/)

if [[ ${#BRANCHES[@]} -eq 0 ]]; then
  echo "No origin/codex/* branches found"
  exit 0
fi

for rb in "${BRANCHES[@]}"; do
  b="${rb#origin/}"
  echo "=== sync $b ==="

  # Reset local branch to remote state
  git checkout -B "$b" "$rb"
  git reset --hard "$rb"

  # Bring latest main into PR branch with automatic conflict policy:
  # prefer current branch content on conflicts, but include all clean changes from main.
  set +e
  git merge --no-edit -X ours "$MAIN_REF"
  mrc=$?
  set -e

  if [[ $mrc -ne 0 ]]; then
    echo "merge had unresolved conflicts for $b, aborting merge and skipping"
    git merge --abort || true
    continue
  fi

  # Push branch update (safe force in case remote changed while we merged)
  git push --force-with-lease origin "HEAD:$b"
done

echo "codex branch sync completed"
