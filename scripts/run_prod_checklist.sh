#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="src:.${PYTHONPATH:+:$PYTHONPATH}"

pytest -q
scripts/smoke.sh
make cards-check
make cards-prepare-approved
make ux-v4-check
