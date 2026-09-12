"""
db.py — SQLite persistence for Aegis negotiation sessions and history (Dev A/C Phase 2).

Schema matches architecture.md §Database Schema:
  - conjunctions
  - negotiation_messages
  - resolutions

Provides CRUD operations to persist completed or escalated negotiation sessions
and query history for the frontend History view.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from contextlib import contextmanager

# Default DB location in backend/app/storage/aegis.db
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "aegis.db"

logger = logging.getLogger("[storage.db]")

CREATE_TABLES_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conjunctions (
    id TEXT PRIMARY KEY,
    primary_id TEXT NOT NULL,
    secondary_id TEXT NOT NULL,
    tca_utc TEXT NOT NULL,
    miss_distance_km REAL NOT NULL,
    relative_velocity_kmps REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS negotiation_messages (
    id TEXT PRIMARY KEY,
    conjunction_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    yield_score REAL,
    justification_text TEXT NOT NULL,
    proposed_action TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conjunction_id) REFERENCES conjunctions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resolutions (
    id TEXT PRIMARY KEY,
    conjunction_id TEXT NOT NULL,
    maneuvering_agent TEXT NOT NULL,
    maneuver_type TEXT NOT NULL,
    delta_v_mps REAL NOT NULL,
    execution_time_utc TEXT NOT NULL,
    expected_min_distance_km REAL NOT NULL,
    residual_risk REAL NOT NULL,
    rationale_text TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (conjunction_id) REFERENCES conjunctions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conjunction ON negotiation_messages(conjunction_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_conjunction ON resolutions(conjunction_id);
CREATE INDEX IF NOT EXISTS idx_conjunctions_created ON conjunctions(created_at DESC);
"""


@contextmanager
def _get_connection(db_path: Path | str | None = None):
    """Creates a connection to SQLite database with foreign keys enabled, closing on exit."""
    path = db_path if db_path is not None else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Initializes the database schema if tables do not exist."""
    with _get_connection(db_path) as conn:
        with conn:
            conn.executescript(CREATE_TABLES_SQL)
    logger.info("Initialized database tables at %s", db_path or DEFAULT_DB_PATH)


def _to_dict(obj: Any) -> dict[str, Any]:
    """Helper to convert Pydantic model, dataclass, or dict to plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__") and not isinstance(obj, dict):
        return dict(obj.__dict__)
    if isinstance(obj, dict):
        return dict(obj)
    raise ValueError(f"Cannot convert object of type {type(obj)} to dict")


def save_conjunction(conjunction: Any, db_path: Path | str | None = None) -> None:
    """Inserts or replaces a conjunction record."""
    c = _to_dict(conjunction)
    # Handle enum values
    status_val = c["status"].value if hasattr(c["status"], "value") else str(c["status"])

    sql = """
    INSERT INTO conjunctions (
        id, primary_id, secondary_id, tca_utc, miss_distance_km,
        relative_velocity_kmps, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status=excluded.status,
        miss_distance_km=excluded.miss_distance_km,
        relative_velocity_kmps=excluded.relative_velocity_kmps;
    """
    with _get_connection(db_path) as conn:
        conn.execute(
            sql,
            (
                str(c["id"]),
                str(c["primary_id"]),
                str(c["secondary_id"]),
                str(c["tca_utc"]),
                float(c["miss_distance_km"]),
                float(c["relative_velocity_kmps"]),
                status_val,
                str(c["created_at"]),
            ),
        )


def save_negotiation_message(message: Any, db_path: Path | str | None = None) -> None:
    """Inserts a negotiation message record."""
    m = _to_dict(message)
    agent_val = m["agent_id"].value if hasattr(m["agent_id"], "value") else str(m["agent_id"])
    action_val = m["proposed_action"].value if hasattr(m["proposed_action"], "value") else str(m["proposed_action"])
    yield_val = float(m["yield_score"]) if m.get("yield_score") is not None else None

    sql = """
    INSERT OR REPLACE INTO negotiation_messages (
        id, conjunction_id, agent_id, round, yield_score,
        justification_text, proposed_action, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    with _get_connection(db_path) as conn:
        conn.execute(
            sql,
            (
                str(m["id"]),
                str(m["conjunction_id"]),
                agent_val,
                int(m["round"]),
                yield_val,
                str(m["justification_text"]),
                action_val,
                str(m["created_at"]),
            ),
        )


def save_resolution(resolution: Any, db_path: Path | str | None = None) -> None:
    """Inserts or replaces a resolution record."""
    r = _to_dict(resolution)
    status_val = r["status"].value if hasattr(r["status"], "value") else str(r["status"])

    sql = """
    INSERT OR REPLACE INTO resolutions (
        id, conjunction_id, maneuvering_agent, maneuver_type, delta_v_mps,
        execution_time_utc, expected_min_distance_km, residual_risk,
        rationale_text, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with _get_connection(db_path) as conn:
        conn.execute(
            sql,
            (
                str(r["id"]),
                str(r["conjunction_id"]),
                str(r["maneuvering_agent"]),
                str(r["maneuver_type"]),
                float(r["delta_v_mps"]),
                str(r["execution_time_utc"]),
                float(r["expected_min_distance_km"]),
                float(r["residual_risk"]),
                str(r["rationale_text"]),
                status_val,
            ),
        )


def save_completed_session(
    conjunction: Any,
    messages: Iterable[Any],
    resolution: Any,
    db_path: Path | str | None = None,
) -> None:
    """
    Atomically saves a completed or escalated negotiation session (conjunction,
    all negotiation transcript messages, and final resolution).
    """
    init_db(db_path)
    c = _to_dict(conjunction)
    r = _to_dict(resolution)

    c_status = c["status"].value if hasattr(c["status"], "value") else str(c["status"])
    r_status = r["status"].value if hasattr(r["status"], "value") else str(r["status"])

    with _get_connection(db_path) as conn:
        # 1. Upsert conjunction
        conn.execute(
            """
            INSERT INTO conjunctions (
                id, primary_id, secondary_id, tca_utc, miss_distance_km,
                relative_velocity_kmps, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                miss_distance_km=excluded.miss_distance_km,
                relative_velocity_kmps=excluded.relative_velocity_kmps;
            """,
            (
                str(c["id"]),
                str(c["primary_id"]),
                str(c["secondary_id"]),
                str(c["tca_utc"]),
                float(c["miss_distance_km"]),
                float(c["relative_velocity_kmps"]),
                c_status,
                str(c["created_at"]),
            ),
        )

        # 2. Insert messages
        for msg in messages:
            m = _to_dict(msg)
            agent_val = m["agent_id"].value if hasattr(m["agent_id"], "value") else str(m["agent_id"])
            action_val = m["proposed_action"].value if hasattr(m["proposed_action"], "value") else str(m["proposed_action"])
            yield_val = float(m["yield_score"]) if m.get("yield_score") is not None else None

            conn.execute(
                """
                INSERT OR REPLACE INTO negotiation_messages (
                    id, conjunction_id, agent_id, round, yield_score,
                    justification_text, proposed_action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(m["id"]),
                    str(m["conjunction_id"]),
                    agent_val,
                    int(m["round"]),
                    yield_val,
                    str(m["justification_text"]),
                    action_val,
                    str(m["created_at"]),
                ),
            )

        # 3. Upsert resolution
        conn.execute(
            """
            INSERT OR REPLACE INTO resolutions (
                id, conjunction_id, maneuvering_agent, maneuver_type, delta_v_mps,
                execution_time_utc, expected_min_distance_km, residual_risk,
                rationale_text, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                str(r["id"]),
                str(r["conjunction_id"]),
                str(r["maneuvering_agent"]),
                str(r["maneuver_type"]),
                float(r["delta_v_mps"]),
                str(r["execution_time_utc"]),
                float(r["expected_min_distance_km"]),
                float(r["residual_risk"]),
                str(r["rationale_text"]),
                r_status,
            ),
        )

    logger.info(
        "Successfully saved negotiation session for conjunction %s (%d messages, status %s)",
        c["id"],
        len(list(messages)),
        r_status,
    )


def get_session_by_conjunction_id(
    conjunction_id: str,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """
    Retrieves a complete session (conjunction, ordered messages, resolution) by conjunction ID.
    Returns None if conjunction not found.
    """
    init_db(db_path)
    with _get_connection(db_path) as conn:
        c_row = conn.execute("SELECT * FROM conjunctions WHERE id = ?", (conjunction_id,)).fetchone()
        if not c_row:
            return None

        m_rows = conn.execute(
            "SELECT * FROM negotiation_messages WHERE conjunction_id = ? ORDER BY round ASC, created_at ASC",
            (conjunction_id,),
        ).fetchall()

        r_row = conn.execute("SELECT * FROM resolutions WHERE conjunction_id = ?", (conjunction_id,)).fetchone()

        return {
            "conjunction": dict(c_row),
            "messages": [dict(m) for m in m_rows],
            "resolution": dict(r_row) if r_row else None,
        }


def get_history_sessions(
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """
    Queries past sessions for the History table, sorted by most recent first.
    Includes conjunction metadata, message count, and final resolution details.
    """
    init_db(db_path)
    with _get_connection(db_path) as conn:
        query = """
        SELECT 
            c.id AS conjunction_id,
            c.primary_id,
            c.secondary_id,
            c.tca_utc,
            c.miss_distance_km,
            c.relative_velocity_kmps,
            c.status AS conjunction_status,
            c.created_at,
            r.id AS resolution_id,
            r.maneuvering_agent,
            r.maneuver_type,
            r.delta_v_mps,
            r.execution_time_utc,
            r.expected_min_distance_km,
            r.residual_risk,
            r.rationale_text,
            r.status AS resolution_status,
            (SELECT COUNT(*) FROM negotiation_messages m WHERE m.conjunction_id = c.id) AS message_count
        FROM conjunctions c
        LEFT JOIN resolutions r ON r.conjunction_id = c.id
        """
        params: list[Any] = []

        if status_filter:
            query += " WHERE c.status = ? OR r.status = ?"
            params.extend([status_filter, status_filter])

        query += " ORDER BY c.created_at DESC, c.tca_utc DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]
