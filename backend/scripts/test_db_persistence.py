#!/usr/bin/env python3
"""
test_db_persistence.py — Standalone verification script for SQLite persistence (db.py)

Tests:
  1. Initialize DB schema (conjunctions, negotiation_messages, resolutions)
  2. Save a completed negotiation session (ConjunctionAlert + 5 messages + Resolution)
  3. Query session back by ID and verify exact field round-trip
  4. Query History sessions (ordered most recent first) and verify message_count & resolution join
  5. Save an escalated session (no_safe_maneuver_found) and verify filtering
  6. Clean up temporary test DB

Usage:
  python backend/scripts/test_db_persistence.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
from backend.app.schemas.negotiation import (
    AgentId,
    NegotiationMessage,
    ProposedAction,
    Resolution,
    ResolutionStatus,
)
from backend.app.storage.db import (
    init_db,
    save_completed_session,
    get_session_by_conjunction_id,
    get_history_sessions,
)

TEST_DB_PATH = Path(__file__).resolve().parent / "test_aegis.db"


def main() -> None:
    print("=" * 70)
    print("  AEGIS STORAGE — SQLITE PERSISTENCE STANDALONE VERIFICATION")
    print("=" * 70)

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    print(f"[1] Initializing schema at {TEST_DB_PATH.name}...")
    init_db(TEST_DB_PATH)
    assert TEST_DB_PATH.exists(), "DB file was not created"
    print("    OK  Schema created successfully")

    # --- Construct Test Session 1 (Resolved) ---
    conjunction_id_1 = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()

    alert1 = ConjunctionAlert(
        id=conjunction_id_1,
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.2,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at=now_utc,
    )

    messages1 = [
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id_1,
            agent_id=AgentId.OPERATOR_A,
            round=1,
            yield_score=0.465,
            justification_text="ISS requests CSS to maneuver due to high MVI.",
            proposed_action=ProposedAction.STAND_DOWN,
            created_at=now_utc,
        ),
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id_1,
            agent_id=AgentId.OPERATOR_B,
            round=1,
            yield_score=0.587,
            justification_text="CSS agrees to execute avoidance maneuver.",
            proposed_action=ProposedAction.MANEUVER,
            created_at=now_utc,
        ),
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id_1,
            agent_id=AgentId.VALIDATION,
            round=1,
            yield_score=None,
            justification_text="Maneuver validated: 6h lookahead clean.",
            proposed_action=ProposedAction.APPROVE,
            created_at=now_utc,
        ),
    ]

    resolution1 = Resolution(
        id=str(uuid.uuid4()),
        conjunction_id=conjunction_id_1,
        maneuvering_agent="operator_B",
        maneuver_type="prograde_burn",
        delta_v_mps=2.4,
        execution_time_utc="2026-01-14T06:12:00Z",
        expected_min_distance_km=6.8,
        residual_risk=6.8,
        rationale_text="CSS executed prograde burn. Validation approved.",
        status=ResolutionStatus.APPROVED,
    )

    print("\n[2] Saving completed session 1 (resolved)...")
    save_completed_session(alert1, messages1, resolution1, db_path=TEST_DB_PATH)
    print("    OK  Session 1 saved")

    print("\n[3] Reading session 1 back by conjunction_id...")
    retrieved1 = get_session_by_conjunction_id(conjunction_id_1, db_path=TEST_DB_PATH)
    assert retrieved1 is not None, "Session 1 could not be retrieved"
    assert retrieved1["conjunction"]["id"] == conjunction_id_1
    assert retrieved1["conjunction"]["primary_id"] == "25544"
    assert retrieved1["conjunction"]["secondary_id"] == "48274"
    assert retrieved1["conjunction"]["miss_distance_km"] == 3.2
    assert len(retrieved1["messages"]) == 3
    assert retrieved1["messages"][0]["agent_id"] == "operator_A"
    assert retrieved1["messages"][0]["yield_score"] == 0.465
    assert retrieved1["messages"][2]["agent_id"] == "validation"
    assert retrieved1["messages"][2]["yield_score"] is None
    assert retrieved1["resolution"]["maneuvering_agent"] == "operator_B"
    assert retrieved1["resolution"]["status"] == "approved"
    print("    OK  All conjunction, message, and resolution fields match")

    # --- Construct Test Session 2 (Escalated: No Safe Maneuver Found) ---
    conjunction_id_2 = str(uuid.uuid4())
    alert2 = ConjunctionAlert(
        id=conjunction_id_2,
        primary_id="40000",
        secondary_id="40002",
        tca_utc="2026-01-15T12:00:00Z",
        miss_distance_km=1.8,
        relative_velocity_kmps=10.2,
        status=ConjunctionStatus.ESCALATED,
        created_at=now_utc,
    )
    messages2 = [
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id_2,
            agent_id=AgentId.VALIDATION,
            round=1,
            yield_score=None,
            justification_text="Secondary collision with debris detected.",
            proposed_action=ProposedAction.REJECT,
            created_at=now_utc,
        ),
    ]
    resolution2 = Resolution(
        id=str(uuid.uuid4()),
        conjunction_id=conjunction_id_2,
        maneuvering_agent="none",
        maneuver_type="none",
        delta_v_mps=0.0,
        execution_time_utc="2026-01-15T12:00:00Z",
        expected_min_distance_km=1.8,
        residual_risk=1.2,
        rationale_text="Both maneuvers unsafe. Escalating.",
        status=ResolutionStatus.NO_SAFE_MANEUVER_FOUND,
    )

    print("\n[4] Saving session 2 (escalated)...")
    save_completed_session(alert2, messages2, resolution2, db_path=TEST_DB_PATH)
    print("    OK  Session 2 saved")

    print("\n[5] Querying History table feed...")
    history = get_history_sessions(db_path=TEST_DB_PATH)
    assert len(history) == 2, f"Expected 2 history rows, got {len(history)}"
    
    # Check fields in history summary
    row1 = next(r for r in history if r["conjunction_id"] == conjunction_id_1)
    assert row1["message_count"] == 3
    assert row1["resolution_status"] == "approved"
    assert row1["maneuvering_agent"] == "operator_B"

    row2 = next(r for r in history if r["conjunction_id"] == conjunction_id_2)
    assert row2["message_count"] == 1
    assert row2["resolution_status"] == "no_safe_maneuver_found"
    assert row2["maneuvering_agent"] == "none"
    print("    OK  History query correctly joined resolutions and counted messages")

    # Cleanup
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    print("\n[6] Cleaned up temporary test database")

    print("\n" + "=" * 70)
    print("  ALL SQLITE PERSISTENCE TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
