import json
import sqlite3
from typing import Any, Optional
from pathlib import Path

try:
    import psycopg2
except Exception:
    psycopg2 = None

from ..config import settings


_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS quiz_sessions (
    session_id TEXT PRIMARY KEY,
    session_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_SQLITE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS quiz_sessions (
    session_id TEXT PRIMARY KEY,
    session_data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _use_postgres() -> bool:
    return bool(settings.DATABASE_URL)


def _sqlite_path() -> Path:
    path = Path(settings.SQLITE_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _json_sessions_dir() -> Path:
    path = Path(settings.JSON_SESSIONS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_session_json(session_id: str, session_data: dict[str, Any]) -> None:
    try:
        export_dir = _json_sessions_dir()
        export_file = export_dir / f"{session_id}.json"

        score = session_data.get("score", 0)
        total_questions = session_data.get("total_questions", 0)
        final_score = round((score / total_questions), 2) if total_questions else 0

        self_confidence = session_data.get("self_confidence")
        if self_confidence is None:
            self_confidence = session_data.get("overall_confidence", 50)

        confidence_per_question = {}
        behavioral_data = session_data.get("behavioral_data", {}) or {}
        questions = session_data.get("questions", []) or []
        for q in questions:
            qid = q.get("id")
            if not qid:
                continue

            q_behavior = behavioral_data.get(qid, {}) or {}
            q_conf = q_behavior.get("face_final_confidence")
            if q_conf is None:
                q_conf = self_confidence

            # Normalize to percentage for easier reading.
            if isinstance(q_conf, (int, float)) and q_conf <= 1:
                q_conf = round(q_conf * 100, 2)

            confidence_per_question[qid] = q_conf

        payload = {
            "final_score": final_score,
            "self_confidence": self_confidence,
            "confidence_per_question": confidence_per_question,
        }
        export_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"Warning: Failed to export session {session_id} to JSON: {e}")


def init_session_store() -> None:
    # Always ensure JSON export directory exists
    _json_sessions_dir()

    if _use_postgres():
        if psycopg2 is None:
            print("⚠️ psycopg2 is not installed. Falling back to SQLite session store.")
        else:
            conn = None
            try:
                conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=5)
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(_TABLE_SQL)
                print("✅ PostgreSQL session store initialized")
                return
            except Exception as e:
                print(f"⚠️ Failed to initialize PostgreSQL session store: {e}. Falling back to SQLite.")
            finally:
                if conn:
                    conn.close()

    try:
        sqlite_db = _sqlite_path()
        with sqlite3.connect(str(sqlite_db)) as conn:
            conn.execute(_SQLITE_TABLE_SQL)
            conn.commit()
        print(f"✅ SQLite session store initialized at {sqlite_db}")
    except Exception as e:
        print(f"⚠️ Failed to initialize SQLite session store: {e}")


def save_session(session_id: str, session_data: dict[str, Any]) -> None:
    # Always keep a human-readable JSON snapshot.
    _save_session_json(session_id, session_data)

    payload = json.dumps(session_data)

    if _use_postgres() and psycopg2 is not None:
        conn = None
        try:
            conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=5)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO quiz_sessions (session_id, session_data)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (session_id)
                    DO UPDATE SET
                        session_data = EXCLUDED.session_data,
                        updated_at = NOW();
                    """,
                    (session_id, payload),
                )
            return
        except Exception as e:
            print(f"Warning: Failed to save session {session_id} to PostgreSQL: {e}. Falling back to SQLite.")
        finally:
            if conn:
                conn.close()

    try:
        sqlite_db = _sqlite_path()
        with sqlite3.connect(str(sqlite_db)) as conn:
            conn.execute(
                """
                INSERT INTO quiz_sessions (session_id, session_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    session_data = excluded.session_data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session_id, payload),
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to save session {session_id} to SQLite: {e}")


def load_session(session_id: str) -> Optional[dict[str, Any]]:
    if _use_postgres() and psycopg2 is not None:
        conn = None
        try:
            conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=5)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_data FROM quiz_sessions WHERE session_id = %s",
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                data = row[0]
                if isinstance(data, str):
                    return json.loads(data)
                return data
        except Exception as e:
            print(f"Warning: Failed to load session {session_id} from PostgreSQL: {e}. Falling back to SQLite.")
        finally:
            if conn:
                conn.close()

    try:
        sqlite_db = _sqlite_path()
        with sqlite3.connect(str(sqlite_db)) as conn:
            cur = conn.execute(
                "SELECT session_data FROM quiz_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return json.loads(row[0])
    except Exception as e:
        print(f"Warning: Failed to load session {session_id} from SQLite: {e}")
        return None
