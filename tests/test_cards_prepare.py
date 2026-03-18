from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'cards_prepare_approved.py'


def test_cards_prepare_approved_uses_dynamic_repo_root(tmp_path: Path) -> None:
    assets_root = tmp_path / 'assets' / 'cards' / 'style-c'
    drafts_root = assets_root / 'drafts'
    drafts_root.mkdir(parents=True)
    original = drafts_root / 'draft-001.jpg'
    original.write_bytes(b'jpg-data')
    manifest_path = tmp_path / 'approved_manifest.json'

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            '--assets-root',
            str(assets_root),
            '--manifest-path',
            str(manifest_path),
            '--smoke',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '[cards-prepare-approved] smoke ok' in result.stdout
    assert original.exists()
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert data['draft_count'] == 1
    assert data['draft_images'][0]['name'] == 'draft-001.jpg'


def test_cards_prepare_approved_does_not_remove_existing_drafts(tmp_path: Path) -> None:
    assets_root = tmp_path / 'assets' / 'cards' / 'style-c'
    drafts_root = assets_root / 'drafts'
    drafts_root.mkdir(parents=True)
    for index in range(2):
        (drafts_root / f'draft-{index}.jpg').write_bytes(f'img-{index}'.encode())

    before = sorted(path.name for path in drafts_root.iterdir())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--assets-root', str(assets_root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    after = sorted(path.name for path in drafts_root.iterdir())
    assert result.returncode == 0, result.stderr
    assert before == after
