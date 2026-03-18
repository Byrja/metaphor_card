from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from app.cards_manifest import validate_manifest


def write_png(path: Path, width: int, height: int) -> None:
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack('>I', len(data))
            + chunk_type
            + data
            + struct.pack('>I', zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    raw = b''.join(b'\x00' + b'\x80\x40\x20' * width for _ in range(height))
    payload = b'\x89PNG\r\n\x1a\n'
    payload += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    payload += chunk(b'IDAT', zlib.compress(raw))
    payload += chunk(b'IEND', b'')
    path.write_bytes(payload)


class CardsValidateTests(unittest.TestCase):
    def test_validate_manifest_accepts_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            style_dir = root / 'assets' / 'cards' / 'style-c'
            drafts = style_dir / 'drafts'
            drafts.mkdir(parents=True)
            write_png(drafts / 'card-1.png', 300, 400)
            manifest = style_dir / 'manifest.yaml'
            manifest.write_text(
                '\n'.join(
                    [
                        'version: 1',
                        'cards:',
                        '  - id: card_001',
                        '    slug: card-001',
                        '    title_ru: "Первая карта"',
                        '    tags: [style-c, approved]',
                        '    source_file: drafts/card-1.png',
                        '    processed_file: processed/card-001.webp',
                        '    status: approved',
                    ]
                ) + '\n',
                encoding='utf-8',
            )

            entries, issues = validate_manifest(manifest)

        self.assertEqual(len(entries), 1)
        self.assertEqual(issues, [])

    def test_validate_manifest_reports_duplicates_and_ratio_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            style_dir = root / 'assets' / 'cards' / 'style-c'
            drafts = style_dir / 'drafts'
            drafts.mkdir(parents=True)
            write_png(drafts / 'wide.png', 300, 300)
            write_png(drafts / 'second.png', 300, 400)
            manifest = style_dir / 'manifest.yaml'
            manifest.write_text(
                '\n'.join(
                    [
                        'version: 1',
                        'cards:',
                        '  - id: dup',
                        '    slug: same',
                        '    title_ru: "wide"',
                        '    tags: [draft]',
                        '    source_file: drafts/wide.png',
                        '    processed_file: processed/dup.webp',
                        '    status: draft',
                        '  - id: dup',
                        '    slug: same',
                        '    title_ru: "second"',
                        '    tags: [draft]',
                        '    source_file: drafts/second.png',
                        '    processed_file: processed/dup.webp',
                        '    status: draft',
                    ]
                ) + '\n',
                encoding='utf-8',
            )

            _, issues = validate_manifest(manifest)

        messages = [issue.message for issue in issues]
        self.assertTrue(any('Duplicate id' in message for message in messages))
        self.assertTrue(any('Duplicate slug' in message for message in messages))
        self.assertTrue(any('processed_file name conflict' in message for message in messages))
        self.assertTrue(any('aspect ratio' in message for message in messages))

    def test_cards_validate_cli_fails_for_missing_file(self):
        result = subprocess.run(
            [sys.executable, 'scripts/cards_validate.py', 'missing.yaml'],
            cwd='/workspace/metaphor_card',
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest not found', result.stderr)


if __name__ == '__main__':
    unittest.main()
