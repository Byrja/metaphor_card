#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="src:.${PYTHONPATH:+:$PYTHONPATH}"
smoke_output="$(python scripts/smoke.py)"
printf '%s\n' "$smoke_output"

if ! grep -F "Сделаем короткий чек-ин без спешки." <<<"$smoke_output" >/dev/null; then
  echo "[smoke.sh] expected v3 /checkin text was not found" >&2
  exit 1
fi

echo "[smoke.sh] v3 /checkin text ok"
