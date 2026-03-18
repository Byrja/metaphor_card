from __future__ import annotations

import json
from pathlib import Path

from scripts.ux_map_guard import run_apply, run_check


def write_v3_map(path: Path, *, source: str, items: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"version": "3", "source": source, "items": items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def valid_items() -> list[dict[str, object]]:
    return [
        {
            "target_file": "app/ux_copy.py",
            "target_symbol": "CHECKIN_TITLE",
            "old_snippet": "Сделаем короткий чек-ин без спешки.",
            "new_snippet": "Сделаем короткий чек-ин без спешки и лишнего давления.",
            "source_key": "content/prompts/microcopy.yaml#checkin.title",
        }
    ]


def test_run_check_accepts_valid_v3_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(map_path, source="runner export 2026-03-18T12:00:00Z", items=valid_items())

    assert run_check(map_path) == 0


def test_run_check_fails_for_empty_v3_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(map_path, source="runner export 2026-03-18T12:00:00Z", items=[])

    assert run_check(map_path) == 1


def test_run_check_fails_for_placeholder_source(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(map_path, source="placeholder export", items=valid_items())

    assert run_check(map_path) == 1


def test_run_check_fails_for_unchanged_snippet(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(
        map_path,
        source="runner export 2026-03-18T12:00:00Z",
        items=[
            {
                "target_file": "app/ux_copy.py",
                "target_symbol": "CHECKIN_TITLE",
                "old_snippet": "Сделаем короткий чек-ин без спешки.",
                "new_snippet": "Сделаем короткий чек-ин без спешки.",
                "source_key": "content/prompts/microcopy.yaml#checkin.title",
            }
        ],
    )

    assert run_check(map_path) == 1


def test_run_apply_accepts_valid_v3_map(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(map_path, source="runner export 2026-03-18T12:00:00Z", items=valid_items())

    assert run_apply(map_path) == 0


def test_run_apply_refuses_unchanged_snippet(tmp_path: Path) -> None:
    map_path = tmp_path / "ux_map_v3.json"
    write_v3_map(
        map_path,
        source="runner export 2026-03-18T12:00:00Z",
        items=[
            {
                "target_file": "app/ux_copy.py",
                "target_symbol": "CHECKIN_TITLE",
                "old_snippet": "Сделаем короткий чек-ин без спешки.",
                "new_snippet": "Сделаем короткий чек-ин без спешки.",
                "source_key": "content/prompts/microcopy.yaml#checkin.title",
            }
        ],
    )

    assert run_apply(map_path) == 1
