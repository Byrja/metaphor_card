from __future__ import annotations

import asyncio
import sys

from app.bot import run
from app.config import SettingsError


def main() -> int:
    try:
        asyncio.run(run())
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
