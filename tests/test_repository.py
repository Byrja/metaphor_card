import sqlite3
import unittest
from pathlib import Path

from metaphor_bot.repository import (
    ActiveFlowState,
    clear_active_flow,
    complete_session,
    get_active_flow,
    get_global_metrics,
    get_scenario_metrics,
    get_user_metrics,
    log_safety_event,
    recent_insights,
    save_insight,
    set_active_flow,
    start_session,
    summarize_patterns,
    upsert_user,
)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for migration in sorted(Path("migrations").glob("*.sql")):
            self.conn.executescript(migration.read_text(encoding="utf-8"))

    def tearDown(self):
        self.conn.close()

    def test_insight_and_history(self):
        user_id = upsert_user(self.conn, 999, "tester", "Test")
        session_id = start_session(self.conn, user_id, "check_in")
        save_insight(self.conn, session_id, user_id, "insight", "step")
        complete_session(self.conn, session_id)

        rows = recent_insights(self.conn, user_id, 5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["insight_text"], "insight")

    def test_log_safety_event(self):
        user_id = upsert_user(self.conn, 1000, "tester2", "Test2")
        session_id = start_session(self.conn, user_id, "free_text")
        log_safety_event(self.conn, user_id, session_id, "не могу дышать", "panic")

        count = self.conn.execute("SELECT COUNT(*) AS c FROM safety_events").fetchone()["c"]
        self.assertEqual(count, 1)

    def test_active_flow_roundtrip(self):
        user_id = upsert_user(self.conn, 1001, "tester3", "Test3")
        session_id = start_session(self.conn, user_id, "situation")
        set_active_flow(self.conn, ActiveFlowState("situation", user_id, session_id, 2, ["a1", "a2"]))

        state = get_active_flow(self.conn, user_id)
        self.assertIsNotNone(state)
        self.assertEqual(state.step, 2)
        self.assertEqual(state.answers, ["a1", "a2"])

        clear_active_flow(self.conn, user_id)
        self.assertIsNone(get_active_flow(self.conn, user_id))

    def test_summarize_patterns(self):
        user_id = upsert_user(self.conn, 1002, "tester4", "Test4")
        session_id = start_session(self.conn, user_id, "save_insight")
        save_insight(self.conn, session_id, user_id, "чувствую тревога и тревога", "больше поддержка")
        patterns = summarize_patterns(self.conn, user_id)
        self.assertTrue(any(token == "тревога" for token, _ in patterns))

    def test_user_metrics(self):
        user_id = upsert_user(self.conn, 1003, "tester5", "Test5")

        s1 = start_session(self.conn, user_id, "day_card")
        complete_session(self.conn, s1, "completed")

        s2 = start_session(self.conn, user_id, "check_in")
        complete_session(self.conn, s2, "aborted")

        save_insight(self.conn, s1, user_id, "инсайт", "шаг")
        log_safety_event(self.conn, user_id, s2, "не могу", "panic")

        metrics = get_user_metrics(self.conn, user_id)
        self.assertEqual(metrics.total_sessions, 2)
        self.assertEqual(metrics.completed_sessions, 1)
        self.assertEqual(metrics.insight_count, 1)
        self.assertEqual(metrics.safety_events, 1)

    def test_global_metrics_and_scenarios(self):
        u1 = upsert_user(self.conn, 2001, "u1", "U1")
        u2 = upsert_user(self.conn, 2002, "u2", "U2")

        s1 = start_session(self.conn, u1, "day_card")
        complete_session(self.conn, s1, "completed")
        s2 = start_session(self.conn, u2, "check_in")
        complete_session(self.conn, s2, "aborted")

        save_insight(self.conn, s1, u1, "insight", "step")
        log_safety_event(self.conn, u2, s2, "panic", "panic")

        metrics = get_global_metrics(self.conn)
        self.assertEqual(metrics.total_users, 2)
        self.assertEqual(metrics.total_sessions, 2)
        self.assertEqual(metrics.completed_sessions, 1)
        self.assertEqual(metrics.total_insights, 1)
        self.assertEqual(metrics.total_safety_events, 1)

        by_scenario = get_scenario_metrics(self.conn)
        self.assertTrue(any(item.scenario == "day_card" and item.completed_sessions == 1 for item in by_scenario))
        self.assertTrue(any(item.scenario == "check_in" and item.completed_sessions == 0 for item in by_scenario))

        # same counts for a 7-day window in fresh test DB
        weekly = get_global_metrics(self.conn, days=7)
        self.assertEqual(weekly.total_sessions, 2)


if __name__ == "__main__":
    unittest.main()
