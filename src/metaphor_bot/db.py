import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def apply_migration(conn: sqlite3.Connection, migration_path: str) -> None:
    with open(migration_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def apply_all_migrations(conn: sqlite3.Connection, migrations_dir: str = "migrations") -> None:
    paths = sorted(Path(migrations_dir).glob("*.sql"))
    for path in paths:
        apply_migration(conn, str(path))
