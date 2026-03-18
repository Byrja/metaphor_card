from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class UXMapError(Exception):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def load_map(map_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UXMapError("missing_map", f"UX map file not found: {map_path}") from exc
    except json.JSONDecodeError as exc:
        raise UXMapError("invalid_json", f"UX map file is not valid JSON: {map_path} ({exc})") from exc

    if not isinstance(data, dict):
        raise UXMapError("invalid_shape", "UX map root must be a JSON object.")
    required_keys = {"version", "source", "items"}
    if not required_keys.issubset(data):
        raise UXMapError("invalid_shape", "UX map root must contain version, source, and items.")
    return data


def validation_error(data: dict[str, Any]) -> UXMapError | None:
    version = str(data.get("version", ""))
    items = data.get("items")
    source = str(data.get("source", ""))

    if not isinstance(items, list):
        return UXMapError("invalid_shape", "UX map field 'items' must be a list.")
    if len(items) == 0:
        return UXMapError("empty_map", "UX map items list is empty.")
    if version == "4" and len(items) < 8:
        return UXMapError("too_few_items", "UX v4 map must contain at least 8 items.")
    if "placeholder" in source.casefold():
        return UXMapError("placeholder_source", "UX map source still contains a placeholder marker.")

    seen_pairs: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return UXMapError("invalid_shape", f"UX map item #{index} must be an object.")

        old_snippet = item.get("old_snippet")
        new_snippet = item.get("new_snippet")
        if isinstance(old_snippet, str) and isinstance(new_snippet, str) and old_snippet == new_snippet:
            return UXMapError(
                "unchanged_snippet",
                f"UX map item #{index} has identical old_snippet and new_snippet.",
            )
        if version == "4":
            target_file = item.get("target_file")
            if isinstance(target_file, str) and isinstance(old_snippet, str):
                pair = (target_file, old_snippet)
                if pair in seen_pairs:
                    return UXMapError(
                        "duplicate_old_snippet",
                        f"UX v4 map item #{index} duplicates target_file/old_snippet pair: {target_file!r}.",
                    )
                seen_pairs.add(pair)
    return None


def print_report(status: str, map_path: Path, *, reason: str | None = None, detail: str | None = None, items_count: int | None = None) -> None:
    print(f"status: {status}")
    print(f"map: {map_path}")
    if reason:
        print(f"reason: {reason}")
    if items_count is not None:
        print(f"items: {items_count}")
    if detail:
        print(f"detail: {detail}")


def run_check(map_path: Path) -> int:
    try:
        data = load_map(map_path)
        error = validation_error(data)
        items_count = len(data.get("items", [])) if isinstance(data.get("items"), list) else None
        if error:
            print_report("failed", map_path, reason=error.reason, detail=error.message, items_count=items_count)
            return 1
    except UXMapError as error:
        print_report("failed", map_path, reason=error.reason, detail=error.message)
        return 1

    print_report("ok", map_path, items_count=len(data["items"]))
    return 0


def run_apply(map_path: Path) -> int:
    try:
        data = load_map(map_path)
        error = validation_error(data)
        items_count = len(data.get("items", [])) if isinstance(data.get("items"), list) else None
        if error:
            print_report("refused", map_path, reason=error.reason, detail=f"Refusing to apply UX map: {error.message}", items_count=items_count)
            return 1
    except UXMapError as error:
        print_report("refused", map_path, reason=error.reason, detail=f"Refusing to apply UX map: {error.message}")
        return 1

    print_report("applied", map_path, items_count=len(data["items"]), detail="UX map passed validation; apply step may proceed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and gate UX patch maps.")
    parser.add_argument("command", choices=("check", "apply"))
    parser.add_argument("--map", dest="map_path", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "check":
        return run_check(args.map_path)
    return run_apply(args.map_path)


if __name__ == "__main__":
    raise SystemExit(main())
