import unittest

from app.memory import extract_theme_scores


class MemoryExtractionTests(unittest.TestCase):
    def test_extract_theme_scores_returns_ranked_scores(self):
        texts = [
            "На работе тревожно, сильное выгорание и напряжение",
            "Хочу снизить нагрузку в работе",
            "В отношениях тоже есть напряжение",
        ]

        scores = extract_theme_scores(texts)
        self.assertGreater(len(scores), 0)
        self.assertEqual(scores[0].key, "work")
        self.assertGreaterEqual(scores[0].score, scores[-1].score)

    def test_extract_theme_scores_empty_when_no_keywords(self):
        texts = ["случайный текст без совпадений", "ещё один нейтральный текст"]
        scores = extract_theme_scores(texts)
        self.assertEqual(scores, [])


if __name__ == "__main__":
    unittest.main()
