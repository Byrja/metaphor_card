from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.polling_guard import PollingAlreadyRunningError, hold_polling_lock


def test_hold_polling_lock_creates_pid_file(tmp_path: Path):
    lock_path = tmp_path / "runtime" / "polling.lock"

    with hold_polling_lock(lock_path.as_posix()):
        assert lock_path.exists()
        assert lock_path.read_text(encoding="utf-8").strip().isdigit()

    assert lock_path.read_text(encoding="utf-8") == ""


def test_hold_polling_lock_rejects_second_process(tmp_path: Path):
    lock_path = tmp_path / "polling.lock"
    script = (
        "from app.polling_guard import hold_polling_lock, PollingAlreadyRunningError\n"
        "import sys\n"
        f"lock_path = {str(lock_path)!r}\n"
        "try:\n"
        "    with hold_polling_lock(lock_path):\n"
        "        print('acquired')\n"
        "except PollingAlreadyRunningError:\n"
        "    print('locked')\n"
        "    sys.exit(7)\n"
    )

    with hold_polling_lock(lock_path.as_posix()):
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

    assert completed.returncode == 7
    assert "locked" in completed.stdout


@pytest.mark.parametrize("message", ["another polling process is already running"])
def test_polling_error_message(tmp_path: Path, message: str):
    lock_path = tmp_path / "polling.lock"

    with hold_polling_lock(lock_path.as_posix()):
        with pytest.raises(PollingAlreadyRunningError, match=message):
            with hold_polling_lock(lock_path.as_posix()):
                pass
