"""
SQLite-backed job application tracker.

Every query below uses parameterized placeholders ("?"), never string
formatting/concatenation of caller input into SQL text. That is the actual
mechanism that blocks SQL injection here -- see
exploits/exploit_sql_injection.py for a live demonstration against this
module, and exploits/vulnerable_reference.py for what the same call would
do if it used f-string SQL instead.

Reference:
- sqlite3 parameterized-query pattern from the Python standard library docs:
  https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT DEFAULT '',
    source_email_id TEXT,
    interview_datetime TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    with _connect(db_path):
        pass


def upsert_application(
    company: str,
    role: str,
    status: str,
    notes: str = "",
    source_email_id: Optional[str] = None,
    interview_datetime: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Insert a new row, or update the most recent row for the same
    (company, role) pair if one already exists. All values are bound as
    parameters -- none are ever interpolated into the SQL string.
    """
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM applications WHERE company = ? AND role = ? "
            "ORDER BY id DESC LIMIT 1",
            (company, role),
        ).fetchone()

        now = _now()
        if existing:
            conn.execute(
                """
                UPDATE applications
                SET status = ?, notes = ?, source_email_id = COALESCE(?, source_email_id),
                    interview_datetime = COALESCE(?, interview_datetime), updated_at = ?
                WHERE id = ?
                """,
                (status, notes, source_email_id, interview_datetime, now, existing["id"]),
            )
            row_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO applications
                    (company, role, status, notes, source_email_id, interview_datetime,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (company, role, status, notes, source_email_id, interview_datetime, now, now),
            )
            row_id = cur.lastrowid

        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (row_id,)
        ).fetchone()
        return dict(row)


def get_applications(status: Optional[str] = None, db_path: Optional[Path] = None) -> list[dict]:
    with _connect(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def count_rows(db_path: Optional[Path] = None) -> int:
    with _connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()["n"]
