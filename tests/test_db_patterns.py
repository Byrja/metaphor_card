import os
import tempfile
import unittest

from app.db import Database
from app.memory import extract_theme_scores


class DbPatternTests(unittest.TestCase):
    def test_replace_and_get_user_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            db = Database(db_path)
            db.init_schema()

            user_id = db.upsert_user(telegram_id=12345, username="u", display_name="User")
            session_id = db.create_session(user_id, "day_card")
            db.complete_session(session_id)

            db.save_insight(session_id, user_id, "На работе тревога", "один приоритет")
            texts = db.get_insight_texts_for_patterns(user_id)
            scores = extract_theme_scores(texts)

            db.replace_user_patterns(user_id, [(x.key, x.score) for x in scores])
            rows = db.get_user_patterns(user_id, limit=5)

            self.assertGreater(len(rows), 0)
            keys = {row["pattern_key"] for row in rows}
            self.assertIn("work", keys)


if __name__ == "__main__":
    unittest.main()
