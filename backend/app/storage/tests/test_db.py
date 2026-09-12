"""
test_db.py — Unit tests for db.py SQLite persistence layer
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

try:
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
        save_conjunction,
        save_negotiation_message,
        save_resolution,
        get_session_by_conjunction_id,
        get_history_sessions,
    )
except ImportError:
    from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from app.schemas.negotiation import (
        AgentId,
        NegotiationMessage,
        ProposedAction,
        Resolution,
        ResolutionStatus,
    )
    from app.storage.db import (
        init_db,
        save_completed_session,
        save_conjunction,
        save_negotiation_message,
        save_resolution,
        get_session_by_conjunction_id,
        get_history_sessions,
    )


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_aegis.db"
    init_db(db_file)
    return db_file


def test_save_and_retrieve_session(temp_db):
    conjunction_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()

    alert = ConjunctionAlert(
        id=conjunction_id,
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.2,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at=now_utc,
    )

    messages = [
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id,
            agent_id=AgentId.OPERATOR_A,
            round=1,
            yield_score=0.465,
            justification_text="ISS stands down.",
            proposed_action=ProposedAction.STAND_DOWN,
            created_at=now_utc,
        ),
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id,
            agent_id=AgentId.OPERATOR_B,
            round=1,
            yield_score=0.587,
            justification_text="CSS maneuvers.",
            proposed_action=ProposedAction.MANEUVER,
            created_at=now_utc,
        ),
        NegotiationMessage(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id,
            agent_id=AgentId.VALIDATION,
            round=1,
            yield_score=None,
            justification_text="Validation approved.",
            proposed_action=ProposedAction.APPROVE,
            created_at=now_utc,
        ),
    ]

    resolution = Resolution(
        id=str(uuid.uuid4()),
        conjunction_id=conjunction_id,
        maneuvering_agent="operator_B",
        maneuver_type="prograde_burn",
        delta_v_mps=2.4,
        execution_time_utc="2026-01-14T06:12:00Z",
        expected_min_distance_km=6.8,
        residual_risk=6.8,
        rationale_text="Resolved via CSS burn.",
        status=ResolutionStatus.APPROVED,
    )

    save_completed_session(alert, messages, resolution, db_path=temp_db)

    session = get_session_by_conjunction_id(conjunction_id, db_path=temp_db)
    assert session is not None
    assert session["conjunction"]["id"] == conjunction_id
    assert session["conjunction"]["primary_id"] == "25544"
    assert session["conjunction"]["secondary_id"] == "48274"
    assert len(session["messages"]) == 3
    assert session["messages"][0]["agent_id"] == "operator_A"
    assert session["messages"][2]["agent_id"] == "validation"
    assert session["resolution"]["maneuvering_agent"] == "operator_B"
    assert session["resolution"]["status"] == "approved"


def test_history_sessions_query(temp_db):
    cid1 = str(uuid.uuid4())
    cid2 = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()

    alert1 = ConjunctionAlert(
        id=cid1,
        primary_id="25544",
        secondary_id="48274",
        tca_utc="2026-01-14T06:12:00Z",
        miss_distance_km=3.2,
        relative_velocity_kmps=7.5,
        status=ConjunctionStatus.RESOLVED,
        created_at="2026-01-14T00:00:00Z",
    )
    res1 = Resolution(
        id=str(uuid.uuid4()),
        conjunction_id=cid1,
        maneuvering_agent="operator_B",
        maneuver_type="prograde_burn",
        delta_v_mps=2.4,
        execution_time_utc="2026-01-14T06:12:00Z",
        expected_min_distance_km=6.8,
        residual_risk=6.8,
        rationale_text="Resolved",
        status=ResolutionStatus.APPROVED,
    )

    alert2 = ConjunctionAlert(
        id=cid2,
        primary_id="40000",
        secondary_id="40001",
        tca_utc="2026-01-15T12:00:00Z",
        miss_distance_km=1.2,
        relative_velocity_kmps=8.0,
        status=ConjunctionStatus.ESCALATED,
        created_at="2026-01-15T00:00:00Z",
    )
    res2 = Resolution(
        id=str(uuid.uuid4()),
        conjunction_id=cid2,
        maneuvering_agent="none",
        maneuver_type="none",
        delta_v_mps=0.0,
        execution_time_utc="2026-01-15T12:00:00Z",
        expected_min_distance_km=1.2,
        residual_risk=1.2,
        rationale_text="Unsafe",
        status=ResolutionStatus.NO_SAFE_MANEUVER_FOUND,
    )

    save_completed_session(alert1, [], res1, db_path=temp_db)
    save_completed_session(alert2, [], res2, db_path=temp_db)

    history = get_history_sessions(db_path=temp_db)
    assert len(history) == 2
    # Ordered by created_at DESC -> cid2 is more recent
    assert history[0]["conjunction_id"] == cid2
    assert history[0]["resolution_status"] == "no_safe_maneuver_found"
    assert history[1]["conjunction_id"] == cid1
    assert history[1]["resolution_status"] == "approved"
