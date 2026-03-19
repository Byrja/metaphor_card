from __future__ import annotations

import argparse

from _bootstrap import ensure_repo_root_on_path

ensure_repo_root_on_path()

from pathlib import Path

from scripts.cards_pipeline import default_assets_root, summarize_drafts, validate_assets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate card assets and optional approved manifest.')
    parser.add_argument('--assets-root', type=Path, default=default_assets_root())
    parser.add_argument('--manifest-path', type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_assets(args.assets_root, args.manifest_path)
    if errors:
        for error in errors:
            print(f'[cards-check] ERROR: {error}')
        return 1
    print(f'[cards-check] ok: {summarize_drafts(args.assets_root)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
