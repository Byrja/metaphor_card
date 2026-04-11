#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_ITEM_KEYS = {"target_file", "old_snippet", "new_snippet", "source_key"}
REPORT_PATH = Path("reports/ux_patch_apply_report.json")


class PatchMapError(Exception):
    """Raised when the patch map cannot be applied safely."""


@dataclass
class PatchItem:
    target_file: str
    old_snippet: str
    new_snippet: str
    source_key: str
    target_symbol: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any], index: int) -> "PatchItem":
        missing = sorted(REQUIRED_ITEM_KEYS - payload.keys())
        if missing:
            raise PatchMapError(f"Item #{index} missing required keys: {', '.join(missing)}")

        unknown = sorted(set(payload.keys()) - (REQUIRED_ITEM_KEYS | {"target_symbol"}))
        if unknown:
            raise PatchMapError(f"Item #{index} has unknown keys: {', '.join(unknown)}")

        values: dict[str, Any] = {
            "target_file": payload["target_file"],
            "old_snippet": payload["old_snippet"],
            "new_snippet": payload["new_snippet"],
            "source_key": payload["source_key"],
            "target_symbol": payload.get("target_symbol"),
        }
        for key, value in values.items():
            if value is None and key == "target_symbol":
                continue
            if not isinstance(value, str):
                raise PatchMapError(f"Item #{index} field '{key}' must be a string")
            if key != "target_symbol" and not value:
                raise PatchMapError(f"Item #{index} field '{key}' must not be empty")
        return cls(**values)

    def log_label(self) -> str:
        suffix = f"::{self.target_symbol}" if self.target_symbol else ""
        return f"{self.target_file}{suffix} [{self.source_key}]"


@dataclass
class ItemResult:
    index: int
    target_file: str
    target_symbol: str | None
    source_key: str
    status: str
    occurrences: int
    message: str
    diff: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "source_key": self.source_key,
            "status": self.status,
            "occurrences": self.occurrences,
            "message": self.message,
            "diff": self.diff,
        }


@dataclass
class RunResult:
    ok: bool
    mode: str
    map_path: str
    report_path: str
    summary: dict[str, int]
    items: list[ItemResult]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "map_path": self.map_path,
            "report_path": self.report_path,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely validate/apply a UX patch-map JSON file.")
    parser.add_argument("--map", required=True, dest="map_path", help="Path to UX patch-map JSON file")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate and render diffs without writing files")
    mode.add_argument("--apply", action="store_true", help="Apply changes after validation")
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(relative_path: str) -> Path:
    root = repo_root()
    resolved = (root / relative_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PatchMapError(f"Target file escapes repository root: {relative_path}") from exc
    return resolved


def load_patch_items(map_path: Path) -> list[PatchItem]:
    if not map_path.exists():
        raise PatchMapError(f"Patch-map file not found: {map_path}")

    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PatchMapError(f"Patch-map JSON is invalid: {exc}") from exc

    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = payload.get("items")
    else:
        raise PatchMapError("Patch-map root must be an array or an object with an 'items' array")

    if not isinstance(raw_items, list):
        raise PatchMapError("Patch-map 'items' must be an array")

    items: list[PatchItem] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            raise PatchMapError(f"Item #{index} must be an object")
        items.append(PatchItem.from_dict(raw_item, index))
    return items


def build_diff(old: str, new: str, target_file: str, label: str) -> str:
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"a/{target_file}::{label}",
        tofile=f"b/{target_file}::{label}",
        lineterm="",
    )
    return "\n".join(diff)


def evaluate_items(items: list[PatchItem]) -> tuple[list[ItemResult], dict[Path, str], list[str]]:
    file_cache: dict[Path, str] = {}
    draft_cache: dict[Path, str] = {}
    results: list[ItemResult] = []
    errors: list[str] = []

    for index, item in enumerate(items, start=1):
        target_path = resolve_repo_path(item.target_file)
        if not target_path.exists():
            message = f"Target file not found: {item.target_file}"
            results.append(
                ItemResult(index, item.target_file, item.target_symbol, item.source_key, "error", 0, message, "")
            )
            errors.append(message)
            continue

        current_text = draft_cache.get(target_path)
        if current_text is None:
            current_text = target_path.read_text(encoding="utf-8")
            file_cache[target_path] = current_text
            draft_cache[target_path] = current_text

        if item.old_snippet == item.new_snippet:
            message = f"No-op patch refused for {item.log_label()}"
            results.append(
                ItemResult(index, item.target_file, item.target_symbol, item.source_key, "error", 0, message, "")
            )
            errors.append(message)
            continue

        occurrences = current_text.count(item.old_snippet)
        if occurrences == 0:
            message = f"Old snippet not found for {item.log_label()}"
            results.append(
                ItemResult(index, item.target_file, item.target_symbol, item.source_key, "error", 0, message, "")
            )
            errors.append(message)
            continue
        if occurrences > 1:
            message = f"Old snippet is ambiguous ({occurrences} matches) for {item.log_label()}"
            results.append(
                ItemResult(index, item.target_file, item.target_symbol, item.source_key, "error", occurrences, message, "")
            )
            errors.append(message)
            continue

        updated_text = current_text.replace(item.old_snippet, item.new_snippet, 1)
        diff = build_diff(item.old_snippet, item.new_snippet, item.target_file, item.source_key)
        draft_cache[target_path] = updated_text
        results.append(
            ItemResult(index, item.target_file, item.target_symbol, item.source_key, "ready", 1, f"Validated {item.log_label()}", diff)
        )

    return results, draft_cache, errors


def write_report(report_path: Path, result: RunResult) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(map_path: str, mode: str) -> RunResult:
    root = repo_root()
    map_file = (root / map_path).resolve() if not Path(map_path).is_absolute() else Path(map_path).resolve()
    report_path = root / REPORT_PATH
    items: list[ItemResult] = []
    errors: list[str] = []

    try:
        patch_items = load_patch_items(map_file)
        items, draft_cache, errors = evaluate_items(patch_items)
        if not errors and mode == "apply":
            for target_path, updated_text in draft_cache.items():
                original_text = target_path.read_text(encoding="utf-8")
                if original_text != updated_text:
                    target_path.write_text(updated_text, encoding="utf-8")
            items = [
                ItemResult(
                    item.index,
                    item.target_file,
                    item.target_symbol,
                    item.source_key,
                    "applied",
                    item.occurrences,
                    item.message.replace("Validated", "Applied", 1),
                    item.diff,
                )
                if item.status == "ready"
                else item
                for item in items
            ]
    except PatchMapError as exc:
        errors.append(str(exc))

    summary = {
        "total": len(items),
        "applied": sum(1 for item in items if item.status == "applied"),
        "ready": sum(1 for item in items if item.status == "ready"),
        "errors": len(errors),
    }
    result = RunResult(
        ok=not errors,
        mode=mode,
        map_path=str(map_file.relative_to(root)) if map_file.is_relative_to(root) else str(map_file),
        report_path=str(REPORT_PATH),
        summary=summary,
        items=items,
        errors=errors,
    )
    write_report(report_path, result)
    return result


def print_result(result: RunResult) -> None:
    status = "OK" if result.ok else "FAIL"
    print(f"[{status}] mode={result.mode} map={result.map_path} report={result.report_path}")
    for item in result.items:
        print(f"- #{item.index} {item.status}: {item.message}")
        if item.diff:
            print(item.diff)
    if result.errors:
        print("Errors:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "apply" if args.apply else "dry-run"
    result = run(args.map_path, mode)
    print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
