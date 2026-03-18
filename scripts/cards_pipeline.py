from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


@dataclass(frozen=True)
class DraftCardImage:
    name: str
    relative_path: str
    size_bytes: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_assets_root() -> Path:
    return repo_root() / 'assets' / 'cards' / 'style-c'


def default_manifest_path(assets_root: Path) -> Path:
    return assets_root / 'approved_manifest.json'


def drafts_dir(assets_root: Path) -> Path:
    return assets_root / 'drafts'


def iter_draft_images(assets_root: Path) -> list[DraftCardImage]:
    root = drafts_dir(assets_root)
    if not root.is_dir():
        raise FileNotFoundError(f'Drafts directory not found: {root}')

    images: list[DraftCardImage] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            images.append(
                DraftCardImage(
                    name=path.name,
                    relative_path=(path.relative_to(repo_root()).as_posix() if path.is_relative_to(repo_root()) else path.as_posix()),
                    size_bytes=path.stat().st_size,
                )
            )
    if not images:
        raise ValueError(f'No draft images found in: {root}')
    return images


def draft_names(assets_root: Path) -> list[str]:
    return [item.name for item in iter_draft_images(assets_root)]


def build_manifest(assets_root: Path) -> dict[str, object]:
    images = iter_draft_images(assets_root)
    return {
        'style': assets_root.name,
        'draft_count': len(images),
        'draft_images': [asdict(item) for item in images],
    }


def write_manifest(manifest_path: Path, manifest: dict[str, object]) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    return manifest_path


def prepare_approved_manifest(assets_root: Path, manifest_path: Path | None = None) -> Path:
    manifest_path = manifest_path or default_manifest_path(assets_root)
    before = draft_names(assets_root)
    manifest = build_manifest(assets_root)
    written = write_manifest(manifest_path, manifest)
    after = draft_names(assets_root)
    if before != after:
        raise RuntimeError('Draft images changed during manifest preparation')
    return written


def validate_assets(assets_root: Path, manifest_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    drafts = iter_draft_images(assets_root)
    if manifest_path is None:
        manifest_path = default_manifest_path(assets_root)

    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        listed = data.get('draft_images', [])
        listed_names = [item.get('name') for item in listed if isinstance(item, dict)]
        actual_names = [item.name for item in drafts]
        if listed_names != actual_names:
            errors.append('Manifest draft_images do not match current draft assets')

    if not drafts:
        errors.append('No draft images found')

    return errors


def summarize_drafts(assets_root: Path) -> str:
    names = draft_names(assets_root)
    return f'{len(names)} draft images: {", ".join(names[:3])}' + ('...' if len(names) > 3 else '')
