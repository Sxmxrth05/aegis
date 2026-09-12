"""
db.py — Dev A (Phase 2 Workstream A)

SQLite Persistence & History Storage Engine.
Provides durable local persistence for conjunction alerts, negotiation transcripts,
and resolutions, matching architecture.md's DB schema exactly.

Provides query functions for Dev D's History table (/history) and REST endpoints.

Ownership: Dev A
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

try:
    from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from backend.app.schemas.negotiation import NegotiationMessage, Resolution, ResolutionStatus
except ImportError:
    from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from app.schemas.negotiation import NegotiationMessage, Resolution, ResolutionStatus


DEFAULT_DB_PATH = Path(__file__).parent / "aegis.db"


def get_db_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection configured with Row factory
    and WAL mode for high reliability and clean dict access.
    """
    if isinstance(db_path, Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path_str = str(db_path)
    else:
        db_path_str = db_path

    conn = sqlite3.connect(db_path_str)
    conn.row_factory = sqlite3.Row
    # Foreign key enforcement & WAL mode (if not in-memory)
    conn.execute("PRAGMA foreign_keys = ON;")
    if db_path_str != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """
    Initializes the SQLite database schema matching architecture.md §Database Schema.
    Idempotent: uses CREATE TABLE IF NOT EXISTS.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. conjunctions table
        cursor.execute("""
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
        """)

        # 2. negotiation_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS negotiation_messages (
                id TEXT PRIMARY KEY,
                conjunction_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                round INTEGER NOT NULL,
                yield_score REAL,
                justification_text TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conjunction_id) REFERENCES conjunctions (id) ON DELETE CASCADE
            );
        """)

        # 3. resolutions table
        cursor.execute("""
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
                FOREIGN KEY (conjunction_id) REFERENCES conjunctions (id) ON DELETE CASCADE
            );
        """)

        # Indexes for fast filtering and joins
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conjunctions_status ON conjunctions (status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conjunction ON negotiation_messages (conjunction_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resolutions_conjunction ON resolutions (conjunction_id);")

        conn.commit()


# ---------------------------------------------------------------------------
# Write Operations (Transactions)
# ---------------------------------------------------------------------------

def save_conjunction_alert(
    alert: ConjunctionAlert | dict,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Inserts or updates a ConjunctionAlert in the database."""
    if isinstance(alert, dict):
        alert = ConjunctionAlert(**alert)

    status_str = alert.status.value if hasattr(alert.status, "value") else str(alert.status)

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO conjunctions (
                id, primary_id, secondary_id, tca_utc,
                miss_distance_km, relative_velocity_kmps, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                miss_distance_km=excluded.miss_distance_km,
                relative_velocity_kmps=excluded.relative_velocity_kmps;
            """,
            (
                alert.id,
                alert.primary_id,
                alert.secondary_id,
                alert.tca_utc,
                alert.miss_distance_km,
                alert.relative_velocity_kmps,
                status_str,
                alert.created_at,
            ),
        )
        conn.commit()


def update_conjunction_status(
    conjunction_id: str,
    status: str | ConjunctionStatus,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Updates the status of an existing conjunction alert."""
    status_str = status.value if hasattr(status, "value") else str(status)
    with get_db_connection(db_path) as conn:
        conn.execute(
            "UPDATE conjunctions SET status = ? WHERE id = ?;",
            (status_str, conjunction_id),
        )
        conn.commit()


def save_negotiation_message(
    message: NegotiationMessage | dict,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Inserts a single NegotiationMessage."""
    if isinstance(message, dict):
        message = NegotiationMessage(**message)

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO negotiation_messages (
                id, conjunction_id, agent_id, round, yield_score,
                justification_text, proposed_action, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                message.id,
                message.conjunction_id,
                message.agent_id.value if hasattr(message.agent_id, "value") else str(message.agent_id),
                message.round,
                message.yield_score,
                message.justification_text,
                message.proposed_action.value if hasattr(message.proposed_action, "value") else str(message.proposed_action),
                message.created_at,
            ),
        )
        conn.commit()


def save_negotiation_messages(
    messages: list[NegotiationMessage | dict],
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Inserts a list of NegotiationMessages in a single transaction."""
    with get_db_connection(db_path) as conn:
        for msg in messages:
            if isinstance(msg, dict):
                msg = NegotiationMessage(**msg)
            conn.execute(
                """
                INSERT OR REPLACE INTO negotiation_messages (
                    id, conjunction_id, agent_id, round, yield_score,
                    justification_text, proposed_action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg.id,
                    msg.conjunction_id,
                    msg.agent_id.value if hasattr(msg.agent_id, "value") else str(msg.agent_id),
                    msg.round,
                    msg.yield_score,
                    msg.justification_text,
                    msg.proposed_action.value if hasattr(msg.proposed_action, "value") else str(msg.proposed_action),
                    msg.created_at,
                ),
            )
        conn.commit()


def save_resolution(
    resolution: Resolution | dict,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Inserts or updates a Resolution."""
    if isinstance(resolution, dict):
        resolution = Resolution(**resolution)

    status_str = resolution.status.value if hasattr(resolution.status, "value") else str(resolution.status)

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO resolutions (
                id, conjunction_id, maneuvering_agent, maneuver_type,
                delta_v_mps, execution_time_utc, expected_min_distance_km,
                residual_risk, rationale_text, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                resolution.id,
                resolution.conjunction_id,
                resolution.maneuvering_agent,
                resolution.maneuver_type,
                resolution.delta_v_mps,
                resolution.execution_time_utc,
                resolution.expected_min_distance_km,
                resolution.residual_risk,
                resolution.rationale_text,
                status_str,
            ),
        )
        conn.commit()


def save_negotiation_session(
    alert: ConjunctionAlert | dict,
    messages: list[NegotiationMessage | dict],
    resolution: Resolution | dict | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """
    Atomic transaction: Saves the conjunction alert, all negotiation messages,
    and the final resolution together in one single transaction.
    """
    if isinstance(alert, dict):
        alert = ConjunctionAlert(**alert)
    if resolution and isinstance(resolution, dict):
        resolution = Resolution(**resolution)

    alert_status_str = alert.status.value if hasattr(alert.status, "value") else str(alert.status)

    with get_db_connection(db_path) as conn:
        # 1. Alert
        conn.execute(
            """
            INSERT OR REPLACE INTO conjunctions (
                id, primary_id, secondary_id, tca_utc,
                miss_distance_km, relative_velocity_kmps, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                alert.id,
                alert.primary_id,
                alert.secondary_id,
                alert.tca_utc,
                alert.miss_distance_km,
                alert.relative_velocity_kmps,
                alert_status_str,
                alert.created_at,
            ),
        )

        # 2. Messages
        for msg in messages:
            if isinstance(msg, dict):
                msg = NegotiationMessage(**msg)
            conn.execute(
                """
                INSERT OR REPLACE INTO negotiation_messages (
                    id, conjunction_id, agent_id, round, yield_score,
                    justification_text, proposed_action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg.id,
                    msg.conjunction_id,
                    msg.agent_id.value if hasattr(msg.agent_id, "value") else str(msg.agent_id),
                    msg.round,
                    msg.yield_score,
                    msg.justification_text,
                    msg.proposed_action.value if hasattr(msg.proposed_action, "value") else str(msg.proposed_action),
                    msg.created_at,
                ),
            )

        # 3. Resolution (optional)
        if resolution:
            res_status_str = resolution.status.value if hasattr(resolution.status, "value") else str(resolution.status)
            conn.execute(
                """
                INSERT OR REPLACE INTO resolutions (
                    id, conjunction_id, maneuvering_agent, maneuver_type,
                    delta_v_mps, execution_time_utc, expected_min_distance_km,
                    residual_risk, rationale_text, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    resolution.id,
                    resolution.conjunction_id,
                    resolution.maneuvering_agent,
                    resolution.maneuver_type,
                    resolution.delta_v_mps,
                    resolution.execution_time_utc,
                    resolution.expected_min_distance_km,
                    resolution.residual_risk,
                    resolution.rationale_text,
                    res_status_str,
                ),
            )

        conn.commit()


# ---------------------------------------------------------------------------
# Read & Query Operations (History Table API)
# ---------------------------------------------------------------------------

def get_conjunction(
    conjunction_id: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[dict]:
    """Retrieves a single ConjunctionAlert as a dictionary."""
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM conjunctions WHERE id = ?;", (conjunction_id,)
        ).fetchone()
        return dict(row) if row else None


def get_negotiation_messages(
    conjunction_id: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict]:
    """Retrieves all NegotiationMessages for a given conjunction, ordered by round/created_at."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM negotiation_messages
            WHERE conjunction_id = ?
            ORDER BY round ASC, created_at ASC;
            """,
            (conjunction_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_resolution(
    conjunction_id: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[dict]:
    """Retrieves the Resolution record for a conjunction."""
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM resolutions WHERE conjunction_id = ?;", (conjunction_id,)
        ).fetchone()
        return dict(row) if row else None


def get_history(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict]:
    """
    Primary query for Dev D's History page (/history).
    Returns a joined list of past conjunctions with their resolution details
    and message counts. Supports filtering by status ('resolved', 'escalated', etc.).
    """
    with get_db_connection(db_path) as conn:
        query = """
            SELECT
                c.id AS conjunction_id,
                c.primary_id,
                c.secondary_id,
                c.tca_utc,
                c.miss_distance_km AS initial_miss_distance_km,
                c.relative_velocity_kmps,
                c.status AS conjunction_status,
                c.created_at AS alert_created_at,
                r.maneuvering_agent,
                r.maneuver_type,
                r.delta_v_mps,
                r.execution_time_utc,
                r.expected_min_distance_km AS post_maneuver_miss_distance_km,
                r.status AS resolution_status,
                r.rationale_text,
                (SELECT COUNT(*) FROM negotiation_messages m WHERE m.conjunction_id = c.id) AS message_count
            FROM conjunctions c
            LEFT JOIN resolutions r ON c.id = r.conjunction_id
        """
        params: list[Any] = []
        if status_filter:
            query += " WHERE c.status = ?"
            params.append(status_filter)

        query += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_full_session_details(
    conjunction_id: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[dict]:
    """
    Returns the complete session record (conjunction alert, negotiation messages
    transcript, and resolution) for detailed modal / history drill-down views.
    """
    alert = get_conjunction(conjunction_id, db_path)
    if not alert:
        return None

    messages = get_negotiation_messages(conjunction_id, db_path)
    resolution = get_resolution(conjunction_id, db_path)

    return {
        "conjunction": alert,
        "transcript": messages,
        "resolution": resolution,
    }
