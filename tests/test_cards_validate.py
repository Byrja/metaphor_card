from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = ROOT / 'scripts' / 'cards_prepare_approved.py'
VALIDATE_SCRIPT = ROOT / 'scripts' / 'cards_validate.py'


def test_cards_validate_accepts_prepared_manifest(tmp_path: Path) -> None:
    assets_root = tmp_path / 'assets' / 'cards' / 'style-c'
    drafts_root = assets_root / 'drafts'
    drafts_root.mkdir(parents=True)
    (drafts_root / 'draft-001.jpg').write_bytes(b'jpg-data')
    manifest_path = tmp_path / 'approved_manifest.json'

    prepare = subprocess.run(
        [
            sys.executable,
            str(PREPARE_SCRIPT),
            '--assets-root',
            str(assets_root),
            '--manifest-path',
            str(manifest_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert prepare.returncode == 0, prepare.stderr

    validate = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            '--assets-root',
            str(assets_root),
            '--manifest-path',
            str(manifest_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert validate.returncode == 0, validate.stderr
    assert '[cards-check] ok:' in validate.stdout


def test_cards_validate_fails_for_stale_manifest(tmp_path: Path) -> None:
    assets_root = tmp_path / 'assets' / 'cards' / 'style-c'
    drafts_root = assets_root / 'drafts'
    drafts_root.mkdir(parents=True)
    (drafts_root / 'draft-001.jpg').write_bytes(b'jpg-data')
    manifest_path = tmp_path / 'approved_manifest.json'

    subprocess.run(
        [
            sys.executable,
            str(PREPARE_SCRIPT),
            '--assets-root',
            str(assets_root),
            '--manifest-path',
            str(manifest_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    (drafts_root / 'draft-002.jpg').write_bytes(b'new-jpg-data')

    validate = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            '--assets-root',
            str(assets_root),
            '--manifest-path',
            str(manifest_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert validate.returncode == 1
    assert 'Manifest draft_images do not match current draft assets' in validate.stdout
