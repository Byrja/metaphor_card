from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib
import logging
import struct

logger = logging.getLogger("metaphor_card.cards_manifest")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TARGET_ASPECT_RATIO = 3 / 4
DEFAULT_ASPECT_TOLERANCE = 0.09
DEFAULT_CANVAS_SIZE = (1536, 2048)
DEFAULT_THUMB_SIZE = (384, 512)


@dataclass(frozen=True)
class ManifestEntry:
    id: str
    slug: str
    title_ru: str
    tags: tuple[str, ...]
    source_file: str
    processed_file: str
    status: str


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    message: str


@dataclass(frozen=True)
class ImageInfo:
    width: int
    height: int
    format: str

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


class ManifestValidationError(RuntimeError):
    pass


class ManifestProcessingError(RuntimeError):
    pass


def _load_yaml_module() -> object:
    try:
        return importlib.import_module("yaml")
    except ModuleNotFoundError as exc:
        raise ManifestValidationError("PyYAML is required to read cards manifest files") from exc


def load_manifest(manifest_path: Path) -> list[ManifestEntry]:
    yaml_module = _load_yaml_module()
    data = yaml_module.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    raw_entries = data.get("cards", [])
    entries: list[ManifestEntry] = []
    for index, item in enumerate(raw_entries, start=1):
        if not isinstance(item, dict):
            raise ManifestValidationError(f"Manifest entry #{index} must be a mapping")
        entries.append(
            ManifestEntry(
                id=str(item.get("id", "")).strip(),
                slug=str(item.get("slug", "")).strip(),
                title_ru=str(item.get("title_ru", "")).strip(),
                tags=tuple(str(tag).strip() for tag in item.get("tags", []) if str(tag).strip()),
                source_file=str(item.get("source_file", "")).strip(),
                processed_file=str(item.get("processed_file", "")).strip(),
                status=str(item.get("status", "")).strip(),
            )
        )
    return entries


def read_image_info(path: Path) -> ImageInfo:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _read_png_info(path)
    if suffix in {".jpg", ".jpeg"}:
        return _read_jpeg_info(path)
    if suffix == ".webp":
        return _read_webp_info(path)
    raise ManifestValidationError(f"Unsupported image extension for metadata: {path.suffix}")


def _read_png_info(path: Path) -> ImageInfo:
    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ManifestValidationError(f"{path} is not a valid PNG file")
        chunk_len = handle.read(4)
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR":
            raise ManifestValidationError(f"{path} is missing PNG IHDR chunk")
        width, height = struct.unpack(">II", handle.read(8))
    return ImageInfo(width=width, height=height, format="png")


def _read_jpeg_info(path: Path) -> ImageInfo:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise ManifestValidationError(f"{path} is not a valid JPEG file")
        while True:
            marker_prefix = handle.read(1)
            if not marker_prefix:
                break
            if marker_prefix != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker in {b"\xd8", b"\xd9"}:
                continue
            segment_length_bytes = handle.read(2)
            if len(segment_length_bytes) != 2:
                break
            segment_length = struct.unpack(">H", segment_length_bytes)[0]
            if segment_length < 2:
                raise ManifestValidationError(f"{path} has an invalid JPEG segment length")
            if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
                handle.read(1)
                height, width = struct.unpack(">HH", handle.read(4))
                return ImageInfo(width=width, height=height, format="jpeg")
            handle.seek(segment_length - 2, 1)
    raise ManifestValidationError(f"Could not determine JPEG dimensions for {path}")


def _read_webp_info(path: Path) -> ImageInfo:
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WEBP":
            raise ManifestValidationError(f"{path} is not a valid WEBP file")
        chunk_header = handle.read(8)
        if len(chunk_header) != 8:
            raise ManifestValidationError(f"{path} is missing WEBP chunk metadata")
        chunk_type = chunk_header[:4]
        chunk_size = struct.unpack("<I", chunk_header[4:])[0]
        payload = handle.read(chunk_size)
        if chunk_type == b"VP8X":
            width = 1 + int.from_bytes(payload[4:7], "little")
            height = 1 + int.from_bytes(payload[7:10], "little")
            return ImageInfo(width=width, height=height, format="webp")
        if chunk_type == b"VP8 ":
            if payload[3:6] != b"\x9d\x01\x2a":
                raise ManifestValidationError(f"{path} has an invalid VP8 header")
            width, height = struct.unpack("<HH", payload[6:10])
            return ImageInfo(width=width & 0x3FFF, height=height & 0x3FFF, format="webp")
        if chunk_type == b"VP8L":
            bits = int.from_bytes(payload[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return ImageInfo(width=width, height=height, format="webp")
    raise ManifestValidationError(f"Unsupported WEBP chunk in {path}")


def validate_manifest(
    manifest_path: Path,
    *,
    aspect_tolerance: float = DEFAULT_ASPECT_TOLERANCE,
) -> tuple[list[ManifestEntry], list[ValidationIssue]]:
    entries = load_manifest(manifest_path)
    issues: list[ValidationIssue] = []
    seen_ids: dict[str, str] = {}
    seen_slugs: dict[str, str] = {}
    processed_targets: dict[str, str] = {}
    manifest_dir = manifest_path.parent

    for entry in entries:
        _validate_required_fields(entry, issues)
        source_path = manifest_dir / entry.source_file
        processed_name = Path(entry.processed_file).name
        if entry.id:
            if entry.id in seen_ids:
                issues.append(ValidationIssue("error", f"Duplicate id '{entry.id}' for slugs '{seen_ids[entry.id]}' and '{entry.slug}'"))
            else:
                seen_ids[entry.id] = entry.slug
        if entry.slug:
            if entry.slug in seen_slugs:
                issues.append(ValidationIssue("error", f"Duplicate slug '{entry.slug}'"))
            else:
                seen_slugs[entry.slug] = entry.id
        if entry.processed_file:
            owner = processed_targets.get(processed_name)
            current_owner = entry.slug or entry.id
            if owner:
                issues.append(ValidationIssue("error", f"processed_file name conflict: '{processed_name}' used by '{owner}' and '{current_owner}'"))
            else:
                processed_targets[processed_name] = current_owner

        if source_path.exists():
            if source_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                issues.append(ValidationIssue("error", f"{entry.slug}: unsupported source extension '{source_path.suffix}'"))
            else:
                try:
                    info = read_image_info(source_path)
                except ManifestValidationError as exc:
                    issues.append(ValidationIssue("error", f"{entry.slug}: {exc}"))
                else:
                    deviation = abs(info.aspect_ratio - TARGET_ASPECT_RATIO)
                    if deviation > aspect_tolerance:
                        issues.append(
                            ValidationIssue(
                                "error",
                                f"{entry.slug}: aspect ratio {info.width}:{info.height} deviates from 3:4 by {deviation:.4f}",
                            )
                        )
        else:
            issues.append(ValidationIssue("error", f"{entry.slug}: source file '{entry.source_file}' does not exist"))

    return entries, issues


def _validate_required_fields(entry: ManifestEntry, issues: list[ValidationIssue]) -> None:
    required = {
        "id": entry.id,
        "slug": entry.slug,
        "title_ru": entry.title_ru,
        "source_file": entry.source_file,
        "processed_file": entry.processed_file,
        "status": entry.status,
    }
    for field_name, value in required.items():
        if not value:
            issues.append(ValidationIssue("error", f"Entry '{entry.slug or entry.id or '<unknown>'}' is missing required field '{field_name}'"))
    if entry.status and entry.status not in {"draft", "approved"}:
        issues.append(ValidationIssue("error", f"{entry.slug}: unsupported status '{entry.status}'"))


def approved_manifest_map(manifest_path: Path) -> dict[str, ManifestEntry]:
    try:
        entries, issues = validate_manifest(manifest_path)
    except (FileNotFoundError, ManifestValidationError) as exc:
        logger.warning("Cards manifest is unavailable or invalid at %s: %s", manifest_path, exc)
        return {}

    errors = [issue.message for issue in issues if issue.level == "error"]
    if errors:
        logger.warning("Cards manifest validation failed at %s: %s", manifest_path, '; '.join(errors))
        return {}
    return {entry.slug: entry for entry in entries if entry.status == "approved"}
