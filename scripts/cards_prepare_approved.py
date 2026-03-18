from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cards_pipeline import default_assets_root, prepare_approved_manifest, summarize_drafts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Prepare approved cards manifest without touching draft assets.')
    parser.add_argument('--assets-root', type=Path, default=default_assets_root())
    parser.add_argument('--manifest-path', type=Path, default=None)
    parser.add_argument('--smoke', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = prepare_approved_manifest(args.assets_root, args.manifest_path)
    print(f'[cards-prepare-approved] manifest: {manifest_path}')
    print(f'[cards-prepare-approved] drafts preserved: {summarize_drafts(args.assets_root)}')
    if args.smoke:
        print('[cards-prepare-approved] smoke ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
