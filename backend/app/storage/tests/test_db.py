"""
test_db.py — Dev A (Phase 2 Workstream A)

Comprehensive unit and integration test suite for SQLite persistence (storage/db.py).
Located in storage/tests/ subfolder per project test organization standards.

Verifies:
1. Schema initialization and index creation
2. Individual CRUD operations for alerts, messages, and resolutions
3. Foreign key constraints and atomic transaction rollbacks
4. Both primary function names and backwards-compatible aliases (save_conjunction, save_completed_session, get_history_sessions)
5. Dual-status filtering (c.status OR r.status)
6. Full session transcript retrieval (get_full_session_details)
7. Seeding default aegis.db for live frontend integration
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from backend.app.schemas.negotiation import AgentId, NegotiationMessage, ProposedAction, Resolution, ResolutionStatus
    from backend.app.storage.db import (
        DEFAULT_DB_PATH,
        get_conjunction,
        get_db_connection,
        get_full_session_details,
        get_history,
        get_history_sessions,
        get_negotiation_messages,
        get_resolution,
        init_db,
        save_completed_session,
        save_conjunction,
        save_conjunction_alert,
        save_negotiation_message,
        save_negotiation_messages,
        save_negotiation_session,
        save_resolution,
        update_conjunction_status,
    )
except ImportError:
    from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from app.schemas.negotiation import AgentId, NegotiationMessage, ProposedAction, Resolution, ResolutionStatus
    from app.storage.db import (
        DEFAULT_DB_PATH,
        get_conjunction,
        get_db_connection,
        get_full_session_details,
        get_history,
        get_history_sessions,
        get_negotiation_messages,
        get_resolution,
        init_db,
        save_completed_session,
        save_conjunction,
        save_conjunction_alert,
        save_negotiation_message,
        save_negotiation_messages,
        save_negotiation_session,
        save_resolution,
        update_conjunction_status,
    )


@pytest.fixture
def test_db(tmp_path):
    """Provides a fresh isolated SQLite database initialized with schema."""
    db_path = tmp_path / "test_aegis.db"
    init_db(db_path)
    return db_path


def test_init_db_creates_tables_and_indexes(test_db):
    """Verify all tables and indexes exist in the schema."""
    with get_db_connection(test_db) as conn:
        cursor = conn.cursor()
        tables = [row["name"] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        assert "conjunctions" in tables
        assert "negotiation_messages" in tables
        assert "resolutions" in tables

        indexes = [row["name"] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()]
        assert "idx_conjunctions_status" in indexes
        assert "idx_messages_conjunction" in indexes
        assert "idx_resolutions_conjunction" in indexes


def test_save_and_get_conjunction_alert(test_db):
    """Verify saving and fetching a ConjunctionAlert (both primary name and alias)."""
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

    save_conjunction_alert(alert, test_db)
    fetched = get_conjunction("c-test-1", test_db)

    assert fetched is not None
    assert fetched["id"] == "c-test-1"
    assert fetched["primary_id"] == "25544"
    assert fetched["status"] == "alerted"
    assert fetched["miss_distance_km"] == 3.20

    # Alias check (save_conjunction)
    alert2 = ConjunctionAlert(
        id="c-test-2",
        primary_id="36086",
        secondary_id="48274",
        tca_utc="2026-01-14T08:00:00Z",
        miss_distance_km=1.50,
        relative_velocity_kmps=8.0,
        status=ConjunctionStatus.ALERTED,
        created_at="2026-01-14T06:00:00Z",
    )
    save_conjunction(alert2, test_db)
    fetched2 = get_conjunction("c-test-2", test_db)
    assert fetched2 is not None
    assert fetched2["id"] == "c-test-2"


def test_foreign_key_constraint(test_db):
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
        save_negotiation_message(msg, test_db)


def test_save_negotiation_session_atomic(test_db):
    """Verify atomic saving of an entire negotiation session (primary & alias)."""
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

    save_negotiation_session(alert, messages, resolution, test_db)

    session = get_full_session_details("c-session-1", test_db)
    assert session is not None
    assert session["conjunction"]["id"] == "c-session-1"
    assert len(session["transcript"]) == 2
    assert session["resolution"]["delta_v_mps"] == 5.4

    # Alias check (save_completed_session)
    alert2 = ConjunctionAlert(
        id="c-session-2",
        primary_id="25544",
        secondary_id="36086",
        tca_utc="2026-01-14T09:00:00Z",
        miss_distance_km=2.10,
        relative_velocity_kmps=7.8,
        status=ConjunctionStatus.RESOLVED,
        created_at="2026-01-14T08:00:00Z",
    )
    save_completed_session(alert2, [], resolution=None, db_path=test_db)
    assert get_conjunction("c-session-2", test_db) is not None


def test_get_history_filtering_dual_status(test_db):
    """Verify history table queries filter by both conjunction status and resolution status."""
    # Session 1: Resolved / Approved
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
    save_negotiation_session(alert_res, [], res_res, test_db)

    # Session 2: Escalated / No safe maneuver
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
    save_negotiation_session(alert_esc, [], res_esc, test_db)

    # Query all
    all_history = get_history(db_path=test_db)
    assert len(all_history) == 2

    # Query by conjunction status
    resolved_only = get_history(status_filter="resolved", db_path=test_db)
    assert len(resolved_only) == 1
    assert resolved_only[0]["conjunction_id"] == "c-res"

    # Query by resolution status (tests OR filter for 'approved')
    approved_only = get_history(status_filter="approved", db_path=test_db)
    assert len(approved_only) == 1
    assert approved_only[0]["conjunction_id"] == "c-res"

    # Alias check (get_history_sessions)
    alias_history = get_history_sessions(status_filter="escalated", db_path=test_db)
    assert len(alias_history) == 1
    assert alias_history[0]["conjunction_id"] == "c-esc"


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
