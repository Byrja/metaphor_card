import unittest

from app.config import (
    DEFAULT_AI_TIMEOUT_SEC,
    DEFAULT_DATABASE_PATH,
    DEFAULT_LOG_LEVEL,
    SettingsError,
    load_settings,
)


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


    def test_ai_settings_are_loaded(self):
        settings = load_settings(
            {
                "BOT_TOKEN": "123:abc",
                "AI_ENABLED": "1",
                "AI_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "secret",
                "OPENROUTER_MODEL": "openai/gpt-4o-mini",
                "AI_TIMEOUT_SEC": "7.5",
            }
        )
        self.assertTrue(settings.ai_enabled)
        self.assertEqual(settings.ai_provider, "openrouter")
        self.assertEqual(settings.openrouter_api_key, "secret")
        self.assertEqual(settings.ai_timeout_sec, 7.5)

    def test_invalid_ai_timeout_is_rejected(self):
        with self.assertRaises(SettingsError):
            load_settings({"BOT_TOKEN": "123:abc", "AI_TIMEOUT_SEC": "0"})

    def test_default_ai_timeout_is_used(self):
        settings = load_settings({"BOT_TOKEN": "123:abc"})
        self.assertEqual(settings.ai_timeout_sec, DEFAULT_AI_TIMEOUT_SEC)


if __name__ == "__main__":
    unittest.main()
