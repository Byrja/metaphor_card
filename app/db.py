import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY,
                  telegram_id BIGINT NOT NULL UNIQUE,
                  username TEXT,
                  display_name TEXT,
                  locale TEXT DEFAULT 'ru',
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                  id INTEGER PRIMARY KEY,
                  user_id INTEGER NOT NULL,
                  scenario_type TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'active',
                  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  completed_at TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS insights (
                  id INTEGER PRIMARY KEY,
                  session_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  insight_text TEXT NOT NULL,
                  small_step_text TEXT,
                  emotion_tags_json TEXT,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(session_id) REFERENCES sessions(id),
                  FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS safety_events (
                  id INTEGER PRIMARY KEY,
                  session_id INTEGER,
                  user_id INTEGER NOT NULL,
                  risk_level TEXT NOT NULL,
                  trigger_source TEXT NOT NULL,
                  trigger_payload_json TEXT,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(session_id) REFERENCES sessions(id),
                  FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS user_patterns (
                  id INTEGER PRIMARY KEY,
                  user_id INTEGER NOT NULL,
                  pattern_key TEXT NOT NULL,
                  score REAL NOT NULL,
                  last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, pattern_key),
                  FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )

    def upsert_user(self, telegram_id: int, username: str | None, display_name: str) -> int:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO users(telegram_id, username, display_name)
                VALUES(?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    display_name = excluded.display_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_id, username, display_name),
            )
            row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            return int(row["id"])

    def create_session(self, user_id: int, scenario_type: str) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                "INSERT INTO sessions(user_id, scenario_type, status) VALUES(?, ?, 'active')",
                (user_id, scenario_type),
            )
            return int(cur.lastrowid)

    def set_session_status(self, session_id: int, status: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, completed_at = ? WHERE id = ?",
                (status, datetime.utcnow().isoformat(), session_id),
            )

    def complete_session(self, session_id: int) -> None:
        self.set_session_status(session_id, "completed")

    def escalate_session(self, session_id: int) -> None:
        self.set_session_status(session_id, "safety_escalated")

    def save_insight(self, session_id: int, user_id: int, insight_text: str, small_step_text: str | None) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO insights(session_id, user_id, insight_text, small_step_text)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, insight_text, small_step_text),
            )

    def log_safety_event(
        self,
        user_id: int,
        risk_level: str,
        trigger_source: str,
        trigger_payload_json: str,
        session_id: int | None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO safety_events(session_id, user_id, risk_level, trigger_source, trigger_payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, risk_level, trigger_source, trigger_payload_json),
            )

    def get_recent_insights(self, user_id: int, limit: int = 5) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT i.created_at, s.scenario_type, i.insight_text, i.small_step_text
                FROM insights i
                JOIN sessions s ON s.id = i.session_id
                WHERE i.user_id = ?
                ORDER BY i.created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return list(rows)

    def get_insight_texts_for_patterns(self, user_id: int, limit: int = 50) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT insight_text, COALESCE(small_step_text, '') AS small_step_text
                FROM insights
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            texts: list[str] = []
            for row in rows:
                texts.append(row["insight_text"])
                if row["small_step_text"]:
                    texts.append(row["small_step_text"])
            return texts

    def replace_user_patterns(self, user_id: int, patterns: list[tuple[str, float]]) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM user_patterns WHERE user_id = ?", (user_id,))
            for key, score in patterns:
                conn.execute(
                    """
                    INSERT INTO user_patterns(user_id, pattern_key, score, last_seen_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, key, score, datetime.utcnow().isoformat()),
                )

    def get_user_patterns(self, user_id: int, limit: int = 5) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT pattern_key, score, last_seen_at
                FROM user_patterns
                WHERE user_id = ?
                ORDER BY score DESC, last_seen_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return list(rows)
