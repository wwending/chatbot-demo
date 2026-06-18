import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_db_path() -> Path:
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.db_path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS keyword_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                reply TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                chunk_id TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                raw_response TEXT NOT NULL,
                final_answer TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def ensure_session(user_id: str, session_id: str | None, title_seed: str = "新会话") -> str:
    init_db()
    now = utc_now()
    with connect() as conn:
        if session_id:
            row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
                return session_id
        new_id = session_id or str(uuid.uuid4())
        title = title_seed[:30] if title_seed else "新会话"
        conn.execute(
            "INSERT INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (new_id, user_id, title, now, now),
        )
        return new_id


def add_message(session_id: str, role: str, content: str, intent: str | None = None) -> int:
    with connect() as conn:
        now = utc_now()
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, intent, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, intent, now),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        return int(cur.lastrowid)


def recent_messages(session_id: str, limit: int = 12) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, intent, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def list_sessions(user_id: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    return [dict(row) for row in rows]


def list_messages(session_id: str) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, intent, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_session(session_id: str) -> bool:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM keyword_hits WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM model_outputs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return True


def save_keyword_hit(session_id: str, message_id: int, keyword: str, reply: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO keyword_hits (session_id, message_id, keyword, reply, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, message_id, keyword, reply, utc_now()),
        )


def save_model_output(
    session_id: str,
    message_id: int,
    model_name: str,
    raw_response: str,
    final_answer: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO model_outputs (
                session_id, message_id, model_name, prompt_tokens, completion_tokens,
                raw_response, final_answer, latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                message_id,
                model_name,
                prompt_tokens,
                completion_tokens,
                raw_response,
                final_answer,
                latency_ms,
                utc_now(),
            ),
        )


def upsert_knowledge_source(file_name: str, file_path: str, chunk_id: str, content: str, metadata: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_sources (file_name, file_path, chunk_id, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                content = excluded.content,
                metadata = excluded.metadata
            """,
            (file_name, file_path, chunk_id, content, json.dumps(metadata, ensure_ascii=False), utc_now()),
        )


def db_ready() -> bool:
    try:
        init_db()
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
