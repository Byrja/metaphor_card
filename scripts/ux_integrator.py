from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACK_ROOT = Path("docs/ux-pack-v3-python")
REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_MAP = Path("docs/UX_PATCH_MAP_PYTHON.md")
ALLOWED_PREFIXES = (Path("docs"), Path("content/prompts"))
APP_PATH_PATTERN = re.compile(r"\bapp/[A-Za-z0-9_./-]+")


class IntegrationValidationError(ValueError):
    """Raised when the UX pack violates integration constraints."""


@dataclass(frozen=True)
class PlannedCopy:
    source: Path
    target: Path

    @property
    def relative_target(self) -> Path:
        return self.target.relative_to(REPO_ROOT)


@dataclass(frozen=True)
class ValidationResult:
    pack_root: Path
    planned_copies: tuple[PlannedCopy, ...]
    patch_map_path: Path



def _normalize_pack_root(pack_root: Path) -> Path:
    if not pack_root.is_absolute():
        pack_root = REPO_ROOT / pack_root
    return pack_root.resolve()



def _is_allowed_target(relative_path: Path) -> bool:
    if relative_path.parts[:2] == ("content", "prompts"):
        return len(relative_path.parts) >= 3
    return bool(relative_path.parts) and relative_path.parts[0] == "docs"



def _collect_pack_files(pack_root: Path) -> list[Path]:
    return sorted(path for path in pack_root.rglob("*") if path.is_file())



def validate_pack(pack_root: Path = DEFAULT_PACK_ROOT) -> ValidationResult:
    resolved_pack_root = _normalize_pack_root(pack_root)
    if not resolved_pack_root.exists():
        raise IntegrationValidationError(f"Pack root does not exist: {resolved_pack_root}")
    if not resolved_pack_root.is_dir():
        raise IntegrationValidationError(f"Pack root is not a directory: {resolved_pack_root}")

    files = _collect_pack_files(resolved_pack_root)
    if not files:
        raise IntegrationValidationError(f"Pack root is empty: {resolved_pack_root}")

    patch_map_path = resolved_pack_root / REQUIRED_MAP
    if not patch_map_path.exists():
        raise IntegrationValidationError(
            "python-real-path-map required: missing docs/UX_PATCH_MAP_PYTHON.md in pack root"
        )

    patch_map_text = patch_map_path.read_text(encoding="utf-8")
    if not APP_PATH_PATTERN.search(patch_map_text):
        raise IntegrationValidationError(
            "python-real-path-map required: docs/UX_PATCH_MAP_PYTHON.md must reference real app/* paths"
        )

    planned_copies: list[PlannedCopy] = []
    invalid_targets: list[str] = []
    for source in files:
        relative_path = source.relative_to(resolved_pack_root)
        if not _is_allowed_target(relative_path):
            invalid_targets.append(relative_path.as_posix())
            continue
        planned_copies.append(PlannedCopy(source=source, target=REPO_ROOT / relative_path))

    if invalid_targets:
        formatted = ", ".join(invalid_targets)
        raise IntegrationValidationError(
            "UX pack contains forbidden targets; only docs/* and content/prompts/* are allowed: "
            f"{formatted}"
        )

    return ValidationResult(
        pack_root=resolved_pack_root,
        planned_copies=tuple(planned_copies),
        patch_map_path=patch_map_path,
    )



def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def print_plan(result: ValidationResult, dry_run: bool) -> None:
    mode = "dry-run" if dry_run else "apply"
    print(f"[ux-integrator] mode={mode}")
    print(f"[ux-integrator] pack_root={_display_path(result.pack_root)}")
    print(f"[ux-integrator] validated patch map={_display_path(result.patch_map_path)}")
    print(f"[ux-integrator] files={len(result.planned_copies)}")
    for copy in result.planned_copies:
        print(f"  - {_display_path(copy.source)} -> {copy.relative_target.as_posix()}")



def apply_pack(pack_root: Path = DEFAULT_PACK_ROOT, dry_run: bool = False) -> ValidationResult:
    result = validate_pack(pack_root)
    print_plan(result, dry_run=dry_run)
    if dry_run:
        return result

    for copy in result.planned_copies:
        copy.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copy.source, copy.target)
    print("[ux-integrator] apply completed")
    return result



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and apply Yandex UX packs")
    parser.add_argument("command", choices=("check", "apply"))
    parser.add_argument(
        "--pack-root",
        default=DEFAULT_PACK_ROOT.as_posix(),
        help="Path to the UX pack root relative to the repository root.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the copy plan without modifying repository files.",
    )
    return parser



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            result = validate_pack(Path(args.pack_root))
            print_plan(result, dry_run=True)
            return 0

        apply_pack(Path(args.pack_root), dry_run=args.dry_run)
        return 0
    except IntegrationValidationError as exc:
        print(f"[ux-integrator] error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
