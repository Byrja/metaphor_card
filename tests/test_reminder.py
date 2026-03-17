import unittest

from app.memory import PatternScore
from app.reminder import build_nudge


class ReminderTests(unittest.TestCase):
    def test_build_nudge_for_empty_data(self):
        text = build_nudge(None)
        self.assertIn("Пока данных", text)

    def test_build_nudge_high_confidence_uses_primary_template(self):
        text = build_nudge(PatternScore(key="work", score=0.7))
        self.assertIn("темы работы", text)

    def test_build_nudge_low_confidence_uses_secondary_template(self):
        text = build_nudge(PatternScore(key="work", score=0.3))
        self.assertIn("Паттерн по работе", text)


if __name__ == "__main__":
    unittest.main()
