#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency is declared in requirements
    yaml = None

PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"<[^<>\n]+>"),
    re.compile(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b", re.IGNORECASE),
)
BROKEN_MARKERS = ("\ufffd",)


class ValidationError(RuntimeError):
    pass


def load_manifest(pack_root: Path) -> dict[str, Any]:
    manifest_path = pack_root / "manifest.json"
    if not manifest_path.exists():
        raise ValidationError(f"Missing manifest: {manifest_path}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid manifest JSON at {manifest_path}: {exc}") from exc



def _validate_destination(destination: str, manifest: dict[str, Any]) -> None:
    allowed_prefixes = tuple(manifest.get("allowed_destination_prefixes", []))
    forbidden_prefixes = tuple(manifest.get("forbidden_destination_prefixes", []))
    forbidden_extensions = tuple(manifest.get("forbidden_extensions", []))

    if not destination.startswith(allowed_prefixes):
        raise ValidationError(f"Destination '{destination}' is outside allowed prefixes {allowed_prefixes}")
    if destination.startswith(forbidden_prefixes):
        raise ValidationError(f"Destination '{destination}' is inside forbidden prefixes {forbidden_prefixes}")
    if destination.endswith(forbidden_extensions):
        raise ValidationError(f"Destination '{destination}' uses a forbidden extension {forbidden_extensions}")



def _validate_placeholders(path: Path, text: str) -> None:
    for marker in BROKEN_MARKERS:
        if marker in text:
            raise ValidationError(f"Broken character marker found in {path}")
    for pattern in PLACEHOLDER_PATTERNS:
        match = pattern.search(text)
        if match:
            raise ValidationError(f"Placeholder '{match.group(0)}' found in {path}")



def _validate_format(path: Path, file_format: str, text: str) -> None:
    if file_format == "json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc
        return

    if file_format == "yaml":
        if yaml is None:
            raise ValidationError("PyYAML is required to validate YAML UX artifacts")
        try:
            yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[union-attr]
            raise ValidationError(f"Invalid YAML in {path}: {exc}") from exc
        return

    raise ValidationError(f"Unsupported format '{file_format}' for {path}")



def validate_pack(pack_root: Path) -> list[str]:
    manifest = load_manifest(pack_root)
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValidationError(f"Manifest at {pack_root / 'manifest.json'} must contain a non-empty 'files' list")

    validated_files: list[str] = []
    for entry in files:
        source = entry.get("source")
        destination = entry.get("destination")
        file_format = entry.get("format")
        if not all(isinstance(value, str) and value for value in (source, destination, file_format)):
            raise ValidationError(f"Manifest entry is incomplete: {entry}")

        _validate_destination(destination, manifest)
        source_path = pack_root / source
        if not source_path.exists():
            raise ValidationError(f"Missing required file: {source_path}")

        text = source_path.read_text(encoding="utf-8")
        _validate_placeholders(source_path, text)
        _validate_format(source_path, file_format, text)
        validated_files.append(source)

    return validated_files



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Yandex UX pack artifacts before integration")
    parser.add_argument(
        "--pack-root",
        default="docs/ux-pack-v3-python",
        help="Path to the UX pack root containing manifest.json",
    )
    args = parser.parse_args(argv)

    pack_root = Path(args.pack_root).resolve()
    try:
        validated_files = validate_pack(pack_root)
    except ValidationError as exc:
        print(f"[ux-check] FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"[ux-check] OK: validated {len(validated_files)} files from {pack_root}")
    for rel_path in validated_files:
        print(f" - {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
