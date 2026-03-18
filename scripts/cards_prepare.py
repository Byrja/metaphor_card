#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cards_manifest import (
    DEFAULT_CANVAS_SIZE,
    DEFAULT_THUMB_SIZE,
    ManifestValidationError,
    read_image_info,
    validate_manifest,
)

try:
    from PIL import Image, ImageOps  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised through integration fallback
    Image = None
    ImageOps = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare approved style-c cards")
    parser.add_argument(
        "manifest",
        nargs="?",
        default="assets/cards/style-c/manifest.yaml",
        help="Path to manifest.yaml",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    parser.add_argument(
        "--only",
        choices=["approved", "draft", "all"],
        default="all",
        help="Filter entries by status",
    )
    return parser


def iter_selected(entries, only: str):
    if only == "all":
        return list(entries)
    return [entry for entry in entries if entry.status == only]


def prepare_entry(manifest_dir: Path, entry, dry_run: bool) -> tuple[Path, Path]:
    source_path = manifest_dir / entry.source_file
    processed_path = manifest_dir / entry.processed_file
    thumb_path = manifest_dir / "thumbs" / f"{entry.slug}.webp"
    if dry_run:
        print(f"DRY-RUN {entry.slug}: {source_path} -> {processed_path} and {thumb_path}")
        return processed_path, thumb_path

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    if Image is None:
        shutil.copyfile(source_path, processed_path)
        shutil.copyfile(source_path, thumb_path)
        return processed_path, thumb_path

    with Image.open(source_path) as image:
        normalized = ImageOps.fit(image.convert("RGB"), DEFAULT_CANVAS_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        normalized.save(processed_path, format="WEBP", quality=95, method=6)
        thumb = ImageOps.fit(image.convert("RGB"), DEFAULT_THUMB_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        thumb.save(thumb_path, format="WEBP", quality=90, method=6)
    return processed_path, thumb_path


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest)
    manifest_dir = manifest_path.parent

    try:
        entries, issues = validate_manifest(manifest_path)
    except FileNotFoundError:
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    except ManifestValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        for issue in errors:
            print(f"ERROR: {issue.message}", file=sys.stderr)
        return 1

    selected = iter_selected(entries, args.only)
    print(f"Selected {len(selected)} of {len(entries)} manifest entries (only={args.only})")
    if Image is None and not args.dry_run:
        print("WARNING: Pillow is unavailable; using byte-copy fallback instead of real WEBP normalization")

    for entry in selected:
        source_info = read_image_info(manifest_dir / entry.source_file)
        processed_path, thumb_path = prepare_entry(manifest_dir, entry, args.dry_run)
        print(
            f"Prepared {entry.slug}: source={source_info.width}x{source_info.height}, output={processed_path}, thumb={thumb_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
