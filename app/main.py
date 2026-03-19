from __future__ import annotations

import asyncio
import sys

from app.bot import run
from app.config import SettingsError, load_settings
from app.polling_guard import PollingAlreadyRunningError, hold_polling_lock


def main() -> int:
    try:
        settings = load_settings()
        with hold_polling_lock(settings.polling_lock_path):
            asyncio.run(run(settings))
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except PollingAlreadyRunningError as exc:
        print(f"Polling lock error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
