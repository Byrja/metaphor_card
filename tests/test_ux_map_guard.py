from __future__ import annotations

import json
from pathlib import Path

from scripts.ux_map_guard import run_apply, run_check


def write_map(path: Path, *, source: str, items: list[dict[str, str]]) -> None:
    path.write_text(
        json.dumps({"source": source, "items": items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_run_check_fails_for_empty_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map.json"
    write_map(map_path, source="runner export", items=[])

    assert run_check(map_path) == 1


def test_run_check_fails_for_placeholder_source(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map.json"
    write_map(map_path, source="placeholder source", items=[{"path": "app/ux_copy.py"}])

    assert run_check(map_path) == 1


def test_run_apply_refuses_empty_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map.json"
    write_map(map_path, source="runner export", items=[])

    assert run_apply(map_path) == 1


def test_run_apply_accepts_valid_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map.json"
    write_map(
        map_path,
        source="runner export 2026-03-18T12:00:00Z",
        items=[{"path": "app/ux_copy.py", "action": "replace_text"}],
    )

    assert run_apply(map_path) == 0
