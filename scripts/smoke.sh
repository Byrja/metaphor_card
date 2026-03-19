#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

smoke_output="$(python scripts/smoke.py)"
printf '%s\n' "$smoke_output"

if ! grep -F "Сделаем короткий чек-ин спокойно и без спешки." <<<"$smoke_output" >/dev/null; then
  echo "[smoke.sh] expected v4 /checkin text was not found" >&2
  exit 1
fi

echo "[smoke.sh] v4 /checkin text ok"

if ! grep -F "Посмотрим на ситуацию через 3 карты." <<<"$smoke_output" >/dev/null; then
  echo "[smoke.sh] expected v4 /situation text was not found" >&2
  exit 1
fi

echo "[smoke.sh] v4 /situation text ok"

if ! grep -F "Если напряжение не снижается, пожалуйста, свяжись с живым специалистом или близким человеком прямо сейчас." <<<"$smoke_output" >/dev/null; then
  echo "[smoke.sh] expected v4 safety microcopy was not found" >&2
  exit 1
fi

echo "[smoke.sh] v4 safety microcopy ok"

prepare_output="$(python scripts/cards_prepare_approved.py --smoke)"
printf '%s\n' "$prepare_output"

if ! grep -F "[cards-prepare-approved] smoke ok" <<<"$prepare_output" >/dev/null; then
  echo "[smoke.sh] cards-prepare-approved smoke failed" >&2
  exit 1
fi

echo "[smoke.sh] cards-prepare-approved smoke ok"
