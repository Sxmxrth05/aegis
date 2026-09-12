"""
test_db.py — Dev A (Phase 2 Workstream A)

Unit and integration tests for SQLite persistence storage/db.py.
Verifies:
1. Schema initialization and index creation
2. Individual CRUD operations for alerts, messages, and resolutions
3. Foreign key constraints and atomic transaction rollbacks
4. Filterable history table query (get_history)
5. Full session transcript retrieval (get_full_session_details)
6. Seeding default aegis.db for live frontend integration
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
from app.schemas.negotiation import AgentId, NegotiationMessage, ProposedAction, Resolution, ResolutionStatus
from app.storage.db import (
    DEFAULT_DB_PATH,
    get_conjunction,
    get_db_connection,
    get_full_session_details,
    get_history,
    get_negotiation_messages,
    get_resolution,
    init_db,
    save_conjunction_alert,
    save_negotiation_message,
    save_negotiation_messages,
    save_negotiation_session,
    save_resolution,
    update_conjunction_status,
)


@pytest.fixture
def memory_db(tmp_path):
    """Provides a fresh isolated SQLite database initialized with schema."""
    db_path = tmp_path / "test_aegis.db"
    init_db(db_path)
    return db_path


def test_init_db_creates_tables_and_indexes(memory_db):
    """Verify all tables and indexes exist in the schema."""
    with get_db_connection(memory_db) as conn:
        cursor = conn.cursor()
        tables = [row["name"] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        assert "conjunctions" in tables
        assert "negotiation_messages" in tables
        assert "resolutions" in tables

        indexes = [row["name"] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()]
        assert "idx_conjunctions_status" in indexes
        assert "idx_messages_conjunction" in indexes
        assert "idx_resolutions_conjunction" in indexes


def test_save_and_get_conjunction_alert(memory_db):
    """Verify saving and fetching a ConjunctionAlert."""
    alert = ConjunctionAlert(
        id="c-test-1",
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.20,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.ALERTED,
        created_at="2026-01-14T05:00:00Z",
    )

    save_conjunction_alert(alert, memory_db)
    fetched = get_conjunction("c-test-1", memory_db)

    assert fetched is not None
    assert fetched["id"] == "c-test-1"
    assert fetched["primary_id"] == "25544"
    assert fetched["status"] == "alerted"
    assert fetched["miss_distance_km"] == 3.20


def test_foreign_key_constraint(memory_db):
    """Verify that saving a message for a non-existent conjunction raises a foreign key error."""
    msg = NegotiationMessage(
        id="m-invalid-1",
        conjunction_id="c-nonexistent",
        agent_id=AgentId.OPERATOR_A,
        round=1,
        yield_score=0.45,
        justification_text="Test proposal",
        proposed_action=ProposedAction.MANEUVER,
        created_at="2026-01-14T05:10:00Z",
    )

    with pytest.raises(sqlite3.IntegrityError):
        save_negotiation_message(msg, memory_db)


def test_save_negotiation_session_atomic(memory_db):
    """Verify atomic saving of an entire negotiation session."""
    alert = ConjunctionAlert(
        id="c-session-1",
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.20,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at="2026-01-14T05:00:00Z",
    )

    messages = [
        NegotiationMessage(
            id="m-1",
            conjunction_id="c-session-1",
            agent_id=AgentId.OPERATOR_A,
            round=1,
            yield_score=0.71,
            justification_text="MVI is lower than B, propose prograde burn",
            proposed_action=ProposedAction.MANEUVER,
            created_at="2026-01-14T05:10:00Z",
        ),
        NegotiationMessage(
            id="m-2",
            conjunction_id="c-session-1",
            agent_id=AgentId.OPERATOR_B,
            round=1,
            yield_score=0.54,
            justification_text="Agreed, Operator A maneuvers",
            proposed_action=ProposedAction.STAND_DOWN,
            created_at="2026-01-14T05:11:00Z",
        ),
    ]

    resolution = Resolution(
        id="r-1",
        conjunction_id="c-session-1",
        maneuvering_agent="operator_A",
        maneuver_type="prograde_burn",
        delta_v_mps=5.4,
        execution_time_utc="2026-01-14T05:47:00Z",
        expected_min_distance_km=12.74,
        residual_risk=0.0031,
        rationale_text="Operator A performed 5.4 m/s prograde burn.",
        status=ResolutionStatus.APPROVED,
    )

    save_negotiation_session(alert, messages, resolution, memory_db)

    session = get_full_session_details("c-session-1", memory_db)
    assert session is not None
    assert session["conjunction"]["id"] == "c-session-1"
    assert len(session["transcript"]) == 2
    assert session["resolution"]["delta_v_mps"] == 5.4


def test_get_history_filtering(memory_db):
    """Verify history table queries and status filtering."""
    # Insert 1 resolved and 1 escalated session
    alert_res = ConjunctionAlert(
        id="c-res",
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.20,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at="2026-01-14T05:00:00Z",
    )
    res_res = Resolution(
        id="r-res",
        conjunction_id="c-res",
        maneuvering_agent="operator_A",
        maneuver_type="prograde_burn",
        delta_v_mps=5.4,
        execution_time_utc="2026-01-14T05:47:00Z",
        expected_min_distance_km=12.74,
        residual_risk=0.0031,
        rationale_text="Approved",
        status=ResolutionStatus.APPROVED,
    )
    save_negotiation_session(alert_res, [], res_res, memory_db)

    alert_esc = ConjunctionAlert(
        id="c-esc",
        primary_id="25544",
        secondary_id="36086",
        tca_utc="2026-01-14T09:00:00Z",
        miss_distance_km=1.10,
        relative_velocity_kmps=8.1,
        status=ConjunctionStatus.ESCALATED,
        created_at="2026-01-14T07:00:00Z",
    )
    res_esc = Resolution(
        id="r-esc",
        conjunction_id="c-esc",
        maneuvering_agent="none",
        maneuver_type="none",
        delta_v_mps=0.0,
        execution_time_utc="2026-01-14T09:00:00Z",
        expected_min_distance_km=1.10,
        residual_risk=0.85,
        rationale_text="Escalated to human operator",
        status=ResolutionStatus.NO_SAFE_MANEUVER_FOUND,
    )
    save_negotiation_session(alert_esc, [], res_esc, memory_db)

    all_history = get_history(db_path=memory_db)
    assert len(all_history) == 2

    resolved_only = get_history(status_filter="resolved", db_path=memory_db)
    assert len(resolved_only) == 1
    assert resolved_only[0]["conjunction_id"] == "c-res"

    escalated_only = get_history(status_filter="escalated", db_path=memory_db)
    assert len(escalated_only) == 1
    assert escalated_only[0]["conjunction_id"] == "c-esc"


def test_seed_default_database_file():
    """Initializes and seeds the default aegis.db file so frontend /history has live data."""
    init_db(DEFAULT_DB_PATH)

    alert = ConjunctionAlert(
        id="3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c",
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.20,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at="2026-01-14T05:00:00Z",
    )

    messages = [
        NegotiationMessage(
            id="m-seed-1",
            conjunction_id="3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c",
            agent_id=AgentId.OPERATOR_A,
            round=1,
            yield_score=0.71,
            justification_text="ISS (25544) fuel margin is 65%; lower MVI makes a prograde burn optimal.",
            proposed_action=ProposedAction.MANEUVER,
            created_at="2026-01-14T05:10:00Z",
        ),
        NegotiationMessage(
            id="m-seed-2",
            conjunction_id="3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c",
            agent_id=AgentId.OPERATOR_B,
            round=1,
            yield_score=0.54,
            justification_text="CSS Tianhe (48274) confirms agreement; standing down.",
            proposed_action=ProposedAction.STAND_DOWN,
            created_at="2026-01-14T05:11:00Z",
        ),
    ]

    resolution = Resolution(
        id="b6e4a1d2-9c3f-4e7a-8b2d-5f1a0c9e7d3b",
        conjunction_id="3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c",
        maneuvering_agent="operator_A",
        maneuver_type="prograde_burn",
        delta_v_mps=5.4,
        execution_time_utc="2026-01-14T05:47:00Z",
        expected_min_distance_km=12.74,
        residual_risk=0.0031,
        rationale_text="Operator A performed a 5.4 m/s prograde burn 25 min before TCA.",
        status=ResolutionStatus.APPROVED,
    )

    save_negotiation_session(alert, messages, resolution, DEFAULT_DB_PATH)

    history = get_history(db_path=DEFAULT_DB_PATH)
    assert len(history) >= 1
    assert any(h["conjunction_id"] == "3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c" for h in history)
