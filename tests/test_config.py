import tempfile
import unittest
from pathlib import Path

from app.config import DEFAULT_DATABASE_PATH, DEFAULT_LOG_LEVEL, SettingsError, load_settings


class ConfigTests(unittest.TestCase):
    def test_requires_real_bot_token(self):
        with self.assertRaises(SettingsError):
            load_settings({"BOT_TOKEN": "put_your_telegram_token_here"})

    def test_invalid_log_level_falls_back_to_info(self):
        settings = load_settings({"BOT_TOKEN": "123:abc", "LOG_LEVEL": "verbose"})
        self.assertEqual(settings.log_level, DEFAULT_LOG_LEVEL)

    def test_invalid_app_env_is_rejected(self):
        with self.assertRaises(SettingsError):
            load_settings({"BOT_TOKEN": "123:abc", "APP_ENV": "staging"})

    def test_blank_database_path_falls_back_to_default(self):
        settings = load_settings({"BOT_TOKEN": "123:abc", "DATABASE_PATH": "   "})
        self.assertEqual(settings.database_path, DEFAULT_DATABASE_PATH)

    def test_default_polling_lock_path_tracks_database_directory(self):
        settings = load_settings({"BOT_TOKEN": "123:abc", "DATABASE_PATH": "var/runtime/app.sqlite3"})
        self.assertEqual(settings.polling_lock_path, "var/runtime/polling.lock")

    def test_in_memory_database_uses_temp_polling_lock(self):
        settings = load_settings({"BOT_TOKEN": "123:abc", "DATABASE_PATH": ":memory:"})
        expected = Path(tempfile.gettempdir()) / "metaphor_card" / "polling.lock"
        self.assertEqual(Path(settings.polling_lock_path), expected)


if __name__ == "__main__":
    unittest.main()
