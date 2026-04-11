#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACK_ROOT="${PACK_ROOT:-$ROOT_DIR/docs/ux-pack-v3-python}"
MODE="dry-run"

if [[ "${1:-}" == "--apply" ]]; then
  MODE="apply"
fi

python "$ROOT_DIR/scripts/validate_ux_pack.py" --pack-root "$PACK_ROOT"

mapfile -t FILE_MAP < <(
  PACK_ROOT="$PACK_ROOT" python - <<'PY'
import json
import os
from pathlib import Path

pack_root = Path(os.environ["PACK_ROOT"])
manifest = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    print(f"{pack_root / entry['source']}\t{Path.cwd() / entry['destination']}")
PY
)

for row in "${FILE_MAP[@]}"; do
  source_path="${row%%$'\t'*}"
  destination_path="${row#*$'\t'}"

  echo "[ux-integrate] diff: ${destination_path#$ROOT_DIR/}"
  if [[ -f "$destination_path" ]]; then
    diff -u "$destination_path" "$source_path" || true
  else
    echo "[ux-integrate] new file will be created from ${source_path#$ROOT_DIR/}"
  fi

  if [[ "$MODE" == "apply" ]]; then
    mkdir -p "$(dirname "$destination_path")"
    cp "$source_path" "$destination_path"
    echo "[ux-integrate] copied -> ${destination_path#$ROOT_DIR/}"
  fi
done

if [[ "$MODE" == "dry-run" ]]; then
  echo "[ux-integrate] dry-run only. Re-run with --apply to copy approved artifacts."
else
  echo "[ux-integrate] apply complete. Runtime code paths were not targeted."
fi
