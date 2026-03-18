import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass


@dataclass
class ActiveFlowState:
    scenario: str
    user_id: int
    session_id: int
    step: int
    answers: list[str]


@dataclass
class UserMetrics:
    total_sessions: int
    completed_sessions: int
    insight_count: int
    safety_events: int


@dataclass
class GlobalMetrics:
    total_users: int
    total_sessions: int
    completed_sessions: int
    total_insights: int
    total_safety_events: int


@dataclass
class ScenarioMetrics:
    scenario: str
    total_sessions: int
    completed_sessions: int


def upsert_user(conn: sqlite3.Connection, telegram_id: int, username: str | None, first_name: str | None) -> int:
    conn.execute(
        """
        INSERT INTO users(telegram_id, username, first_name)
        VALUES(?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
        """,
        (telegram_id, username, first_name),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    return int(row["id"])


def start_session(conn: sqlite3.Connection, user_id: int, scenario: str) -> int:
    cur = conn.execute(
        "INSERT INTO sessions(user_id, scenario, status) VALUES (?, ?, 'active')",
        (user_id, scenario),
    )
    conn.commit()
    return int(cur.lastrowid)


def complete_session(conn: sqlite3.Connection, session_id: int, status: str = "completed") -> None:
    conn.execute(
        "UPDATE sessions SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, session_id),
    )
    conn.commit()


def save_message(conn: sqlite3.Connection, session_id: int, role: str, message_text: str) -> None:
    conn.execute(
        "INSERT INTO session_messages(session_id, role, message_text) VALUES (?, ?, ?)",
        (session_id, role, message_text),
    )
    conn.commit()


def save_insight(conn: sqlite3.Connection, session_id: int, user_id: int, insight_text: str, next_step: str | None) -> None:
    conn.execute(
        "INSERT INTO insights(session_id, user_id, insight_text, next_step) VALUES (?, ?, ?, ?)",
        (session_id, user_id, insight_text, next_step),
    )
    conn.commit()


def recent_insights(conn: sqlite3.Connection, user_id: int, limit: int = 5) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT insight_text, next_step, created_at
        FROM insights
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return list(rows)


def summarize_patterns(conn: sqlite3.Connection, user_id: int, limit: int = 30) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT insight_text, COALESCE(next_step, '') as next_step FROM insights WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    if not rows:
        return []

    stopwords = {
        "что",
        "как",
        "это",
        "меня",
        "сейчас",
        "очень",
        "хочу",
        "нужно",
        "где",
        "когда",
        "чтобы",
        "себя",
        "шаг",
    }
    words: list[str] = []
    for row in rows:
        combined = f"{row['insight_text']} {row['next_step']}".lower()
        tokens = re.findall(r"[а-яёa-z]{4,}", combined)
        words.extend(token for token in tokens if token not in stopwords)

    return Counter(words).most_common(5)


def get_user_metrics(conn: sqlite3.Connection, user_id: int) -> UserMetrics:
    total_sessions = conn.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]
    completed_sessions = conn.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ? AND status = 'completed'",
        (user_id,),
    ).fetchone()["c"]
    insight_count = conn.execute(
        "SELECT COUNT(*) AS c FROM insights WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]
    safety_events = conn.execute(
        "SELECT COUNT(*) AS c FROM safety_events WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]
    return UserMetrics(
        total_sessions=int(total_sessions),
        completed_sessions=int(completed_sessions),
        insight_count=int(insight_count),
        safety_events=int(safety_events),
    )


def _time_filter(column: str, days: int | None) -> tuple[str, tuple]:
    if days is None:
        return "", ()
    return f" AND {column} >= datetime('now', ?)", (f"-{days} day",)


def get_global_metrics(conn: sqlite3.Connection, days: int | None = None) -> GlobalMetrics:
    user_filter, user_args = _time_filter("created_at", days)
    session_filter, session_args = _time_filter("started_at", days)
    insight_filter, insight_args = _time_filter("created_at", days)
    safety_filter, safety_args = _time_filter("created_at", days)

    total_users = conn.execute(f"SELECT COUNT(*) AS c FROM users WHERE 1=1{user_filter}", user_args).fetchone()["c"]
    total_sessions = conn.execute(f"SELECT COUNT(*) AS c FROM sessions WHERE 1=1{session_filter}", session_args).fetchone()["c"]
    completed_sessions = conn.execute(
        f"SELECT COUNT(*) AS c FROM sessions WHERE status = 'completed'{session_filter}",
        session_args,
    ).fetchone()["c"]
    total_insights = conn.execute(f"SELECT COUNT(*) AS c FROM insights WHERE 1=1{insight_filter}", insight_args).fetchone()["c"]
    total_safety_events = conn.execute(
        f"SELECT COUNT(*) AS c FROM safety_events WHERE 1=1{safety_filter}",
        safety_args,
    ).fetchone()["c"]

    return GlobalMetrics(
        total_users=int(total_users),
        total_sessions=int(total_sessions),
        completed_sessions=int(completed_sessions),
        total_insights=int(total_insights),
        total_safety_events=int(total_safety_events),
    )


def get_scenario_metrics(conn: sqlite3.Connection, days: int | None = None) -> list[ScenarioMetrics]:
    session_filter, session_args = _time_filter("started_at", days)
    rows = conn.execute(
        f"""
        SELECT scenario,
               COUNT(*) AS total_sessions,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_sessions
        FROM sessions
        WHERE 1=1{session_filter}
        GROUP BY scenario
        ORDER BY total_sessions DESC
        """,
        session_args,
    ).fetchall()
    return [
        ScenarioMetrics(
            scenario=row["scenario"],
            total_sessions=int(row["total_sessions"]),
            completed_sessions=int(row["completed_sessions"] or 0),
        )
        for row in rows
    ]


def log_safety_event(conn: sqlite3.Connection, user_id: int, session_id: int, trigger_text: str, trigger_category: str) -> None:
    conn.execute(
        """
        INSERT INTO safety_events(user_id, session_id, trigger_text, trigger_category)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, session_id, trigger_text, trigger_category),
    )
    conn.commit()


def set_active_flow(conn: sqlite3.Connection, state: ActiveFlowState) -> None:
    conn.execute(
        """
        INSERT INTO active_flows(user_id, session_id, scenario, step, answers_json, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            session_id=excluded.session_id,
            scenario=excluded.scenario,
            step=excluded.step,
            answers_json=excluded.answers_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (state.user_id, state.session_id, state.scenario, state.step, json.dumps(state.answers, ensure_ascii=False)),
    )
    conn.commit()


def get_active_flow(conn: sqlite3.Connection, user_id: int) -> ActiveFlowState | None:
    row = conn.execute(
        "SELECT user_id, session_id, scenario, step, answers_json FROM active_flows WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return ActiveFlowState(
        scenario=row["scenario"],
        user_id=int(row["user_id"]),
        session_id=int(row["session_id"]),
        step=int(row["step"]),
        answers=json.loads(row["answers_json"]),
    )


def clear_active_flow(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM active_flows WHERE user_id = ?", (user_id,))
    conn.commit()
