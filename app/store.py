from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                request_payload TEXT NOT NULL,
                response_payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                consent INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_run(run_id: str, request_payload: dict, response_payload: dict) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs(run_id, created_at, request_payload, response_payload) VALUES (?, ?, ?, ?)",
            (run_id, now, json.dumps(request_payload), json.dumps(response_payload)),
        )


def get_run(run_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return {
            "run_id": row["run_id"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "request_payload": json.loads(row["request_payload"]),
            "response_payload": json.loads(row["response_payload"]),
        }


def save_lead(run_id: str, email: str, company: str | None, consent: bool) -> tuple[int, datetime]:
    created_at = datetime.utcnow()
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO leads(run_id, email, company, consent, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, email, company, int(consent), created_at.isoformat()),
        )
        return cursor.lastrowid, created_at
