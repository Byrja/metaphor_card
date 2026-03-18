#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cards_manifest import validate_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate style-c cards manifest")
    parser.add_argument(
        "manifest",
        nargs="?",
        default="assets/cards/style-c/manifest.yaml",
        help="Path to manifest.yaml",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest)

    try:
        entries, issues = validate_manifest(manifest_path)
    except FileNotFoundError:
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(entries)} manifest entries from {manifest_path}")
    if not issues:
        print("OK: no validation issues found")
        return 0

    for issue in issues:
        print(f"{issue.level.upper()}: {issue.message}")
    return 1 if any(issue.level == 'error' for issue in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
