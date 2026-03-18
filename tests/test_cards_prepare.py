from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_cards_validate import write_png


class CardsPrepareTests(unittest.TestCase):
    def test_cards_prepare_dry_run_filters_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            style_dir = root / 'assets' / 'cards' / 'style-c'
            drafts = style_dir / 'drafts'
            drafts.mkdir(parents=True)
            write_png(drafts / 'approved.png', 300, 400)
            write_png(drafts / 'draft.png', 300, 400)
            manifest = style_dir / 'manifest.yaml'
            manifest.write_text(
                '\n'.join(
                    [
                        'version: 1',
                        'cards:',
                        '  - id: card_001',
                        '    slug: approved-card',
                        '    title_ru: "Approved"',
                        '    tags: [approved]',
                        '    source_file: drafts/approved.png',
                        '    processed_file: processed/approved-card.webp',
                        '    status: approved',
                        '  - id: card_002',
                        '    slug: draft-card',
                        '    title_ru: "Draft"',
                        '    tags: [draft]',
                        '    source_file: drafts/draft.png',
                        '    processed_file: processed/draft-card.webp',
                        '    status: draft',
                    ]
                ) + '\n',
                encoding='utf-8',
            )

            result = subprocess.run(
                [sys.executable, 'scripts/cards_prepare.py', str(manifest), '--dry-run', '--only', 'approved'],
                cwd='/workspace/metaphor_card',
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Selected 1 of 2 manifest entries', result.stdout)
        self.assertIn('approved-card', result.stdout)
        self.assertNotIn('draft-card', result.stdout)

    def test_cards_prepare_writes_processed_and_thumb_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            style_dir = root / 'assets' / 'cards' / 'style-c'
            drafts = style_dir / 'drafts'
            drafts.mkdir(parents=True)
            source_path = drafts / 'approved.png'
            write_png(source_path, 300, 400)
            source_bytes = source_path.read_bytes()
            manifest = style_dir / 'manifest.yaml'
            manifest.write_text(
                '\n'.join(
                    [
                        'version: 1',
                        'cards:',
                        '  - id: card_001',
                        '    slug: approved-card',
                        '    title_ru: "Approved"',
                        '    tags: [approved]',
                        '    source_file: drafts/approved.png',
                        '    processed_file: processed/approved-card.webp',
                        '    status: approved',
                    ]
                ) + '\n',
                encoding='utf-8',
            )

            result = subprocess.run(
                [sys.executable, 'scripts/cards_prepare.py', str(manifest), '--only', 'approved'],
                cwd='/workspace/metaphor_card',
                capture_output=True,
                text=True,
                check=False,
            )

            processed_path = style_dir / 'processed' / 'approved-card.webp'
            thumb_path = style_dir / 'thumbs' / 'approved-card.webp'
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(processed_path.exists())
            self.assertTrue(thumb_path.exists())
            self.assertEqual(processed_path.read_bytes(), source_bytes)
            self.assertEqual(thumb_path.read_bytes(), source_bytes)


if __name__ == '__main__':
    unittest.main()
