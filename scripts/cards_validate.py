from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cards_pipeline import default_assets_root, summarize_drafts, validate_assets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate card assets and optional approved manifest.')
    parser.add_argument('--assets-root', type=Path, default=default_assets_root())
    parser.add_argument('--manifest-path', type=Path, default=None)
    parser.add_argument('--content-root', type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_assets(args.assets_root, args.manifest_path, args.content_root)
    if errors:
        for error in errors:
            print(f'[cards-check] ERROR: {error}')
        return 1
    print(f'[cards-check] ok: {summarize_drafts(args.assets_root)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
