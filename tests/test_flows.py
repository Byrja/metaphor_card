import unittest

from metaphor_bot.flows import render_check_in_summary, render_patterns_summary, render_situation_summary


class FlowSummaryTests(unittest.TestCase):
    def test_render_check_in_summary(self):
        insight, step = render_check_in_summary(["тревога", "хочу ясности", "пройтись 10 минут"])
        self.assertIn("Чувство: тревога", insight)
        self.assertEqual(step, "пройтись 10 минут")

    def test_render_situation_summary(self):
        insight, step = render_situation_summary(["застрял", "страх ошибки", "поддержка коллег", "сделаю черновик"])
        self.assertIn("Что поможет: поддержка коллег", insight)
        self.assertEqual(step, "сделаю черновик")

    def test_render_patterns_summary(self):
        text = render_patterns_summary([("тревога", 3), ("поддержка", 2)])
        self.assertIn("тревога", text)
        self.assertIn("поддержка", text)


if __name__ == "__main__":
    unittest.main()
