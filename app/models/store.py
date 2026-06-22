"""Almacenamiento en memoria (MVP1) y SQLite (MVP2)."""
import json
import sqlite3
import uuid
from pathlib import Path

from app.config import DB_PATH
from app.models.schemas import SessionState


class SessionStore:
    """Store híbrido: memoria + persistencia SQLite opcional."""

    def __init__(self, use_sqlite: bool = True):
        self._memory: dict[str, SessionState] = {}
        self._use_sqlite = use_sqlite
        if use_sqlite:
            self._init_db()

    def _init_db(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def create(self) -> str:
        sid = str(uuid.uuid4())
        self._memory[sid] = SessionState(session_id=sid)
        return sid

    def get(self, session_id: str) -> SessionState | None:
        if session_id in self._memory:
            return self._memory[session_id]
        if self._use_sqlite:
            loaded = self._load_sqlite(session_id)
            if loaded:
                self._memory[session_id] = loaded
                return loaded
        return None

    def save(self, state: SessionState) -> None:
        self._memory[state.session_id] = state
        if self._use_sqlite:
            self._save_sqlite(state)

    def delete(self, session_id: str) -> None:
        self._memory.pop(session_id, None)
        if self._use_sqlite:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def _save_sqlite(self, state: SessionState) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, data) VALUES (?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (state.session_id, state.model_dump_json()),
            )

    def _load_sqlite(self, session_id: str) -> SessionState | None:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        return SessionState.model_validate(json.loads(row[0]))


store = SessionStore(use_sqlite=True)
