import unittest

from metaphor_bot.safety import detect_red_flag


class SafetyTests(unittest.TestCase):
    def test_detects_suicide_keyword(self):
        self.assertEqual(detect_red_flag("иногда думаю покончить с собой"), "suicide")

    def test_returns_none_for_regular_text(self):
        self.assertIsNone(detect_red_flag("хочу сделать небольшой шаг и отдохнуть"))


if __name__ == "__main__":
    unittest.main()
