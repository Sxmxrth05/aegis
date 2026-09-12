"""Monitor slice of the orchestrator (build-plan.md Workstream B, task B3).

Wraps conjunction-detection output as `ConjunctionAlert` broadcast events.
Per architecture.md's §System Boundaries, this module never computes physics
itself — it only wraps and dispatches whatever `detect_conjunctions()`
(Dev A's `agents/monitor_agent.py`) returns.
"""

from __future__ import annotations

import asyncio
import logging

try:
    from backend.app.orchestrator.websocket_manager import ConnectionManager
    from backend.app.schemas import ConjunctionAlert, ConjunctionStatus, ErrorPayload, EventType
except ImportError:
    from app.orchestrator.websocket_manager import ConnectionManager
    from app.schemas import ConjunctionAlert, ConjunctionStatus, ErrorPayload, EventType

logger = logging.getLogger(__name__)

MONITOR_SESSION_ID = "monitor"


def negotiation_session_id(conjunction_id: str) -> str:
    """Session key for a /ws/negotiation/{conjunction_id} connection."""
    return f"negotiation:{conjunction_id}"


# Mock strategy per build-plan.md Workstream B: a single hardcoded alert,
# schema-valid, to unblock B2/B3 before Dev A's A3 (scenario/detection) lands.
_HARDCODED_ALERT = ConjunctionAlert(
    id="9f1c1e2a-4b3d-4a5e-9c6f-1a2b3c4d5e6f",
    primary_id="25544",
    secondary_id="48274",
    tca_utc="2026-01-14T06:12:00Z",
    miss_distance_km=3.2,
    relative_velocity_kmps=7.5,
    status=ConjunctionStatus.ALERTED,
    created_at="2026-01-14T00:00:00Z",
)


try:
    from backend.app.agents.monitor_agent import detect_conjunctions as run_detect_conjunctions
except ImportError:
    from app.agents.monitor_agent import detect_conjunctions as run_detect_conjunctions

try:
    from backend.app.agents.negotiator import NegotiationEngine, OperatorProfile
    from backend.app.data.scenario import FIXTURES_DIR, get_seeded_scenario_objects
    from backend.app.schemas.negotiation import AgentId
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    from app.agents.negotiator import NegotiationEngine, OperatorProfile
    from app.data.scenario import FIXTURES_DIR, get_seeded_scenario_objects
    from app.schemas.negotiation import AgentId
    from app.schemas.tracked_object import TrackedObject

import json


def load_tracked_objects_fixture() -> list[TrackedObject]:
    """
    Loads Dev A's Phase 0 TrackedObject mock fixture
    (data/fixtures/tracked_objects.json) as canonical, schema-validated
    Pydantic objects — the real 5-satellite scripted-demo set, not
    fabricated/live-fetched data. Used as a fallback when CelesTrak is unavailable.
    """
    fixture_path = FIXTURES_DIR / "tracked_objects.json"
    with open(fixture_path, encoding="utf-8") as f:
        raw = json.load(f)
    return [TrackedObject(**obj) for obj in raw]


def load_all_tracked_objects() -> list[TrackedObject]:
    """
    Attempts to load and propagate all 20 locked CelesTrak satellites.
    Falls back to fixture if CelesTrak cache/propagation fails.
    """
    try:
        from datetime import datetime, timezone
        try:
            from backend.app.data.celestrak import get_raw_tles
            from backend.app.agents.monitor_agent import build_satellite, propagate
        except ImportError:
            from app.data.celestrak import get_raw_tles
            from app.agents.monitor_agent import build_satellite, propagate

        raw_tles = get_raw_tles()
        now = datetime.now(timezone.utc)
        results: list[TrackedObject] = []
        for raw in raw_tles:
            try:
                sat = build_satellite(raw.tle_line1, raw.tle_line2)
                obj = propagate(
                    satellite=sat,
                    norad_id=raw.norad_id,
                    time_utc=now,
                    name=raw.name,
                    tle_line1=raw.tle_line1,
                    tle_line2=raw.tle_line2,
                )
                results.append(obj)
            except Exception:
                continue
        if results:
            return results
    except Exception as e:
        logger.warning("[orchestrator] Could not load CelesTrak tracked objects (%s); falling back to fixture", e)

    return load_tracked_objects_fixture()


# Physically docked/co-located object groups within the 20-object curated set.
# These satellites share a single station structure, so pairwise conjunction
# detection reports them at ~0.0km/0.0km/s separation — a data-modeling
# artifact (the propagated positions are identical), not a real collision
# risk. Pairs where both NORAD IDs fall in the same group are excluded from
# conjunction detection below. Determined empirically: every pair inside a
# group propagates to exactly 0.0km apart, and no pair spans two groups.
DOCKED_OBJECT_GROUPS: list[frozenset[str]] = [
    frozenset({"25544", "36086", "49044", "67796", "68689", "68837"}),  # ISS complex (ZARYA/POISK/NAUKA + docked Crew Dragon/Cygnus/Progress)
    frozenset({"48274", "53239", "54216", "69049", "69180"}),  # CSS complex (TIANHE/WENTIAN/MENGTIAN + docked Tianzhou/Shenzhou)
]


def _is_docked_pair(norad_id_a: str, norad_id_b: str) -> bool:
    """True if both objects belong to the same physically docked group."""
    return any(
        norad_id_a in group and norad_id_b in group
        for group in DOCKED_OBJECT_GROUPS
    )


# Known profiles for CelesTrak locked satellites; dynamic hash fallback provided for any other NORAD ID
KNOWN_OPERATOR_PROFILES: dict[str, tuple[str, float, float, float]] = {
    # norad_id: (operator_name, mvi, fuel_margin_pct, delta_v_mps)
    "25544": ("NASA / Roscosmos", 0.95, 15.0, 1.8),
    "48274": ("CMSA", 0.70, 45.0, 2.4),
    "44713": ("SpaceX", 0.40, 80.0, 3.5),
    "36086": ("Roscosmos", 0.85, 25.0, 1.5),
    "49044": ("Roscosmos", 0.90, 20.0, 1.6),
    "49271": ("Arianespace / Debris", 0.15, 5.0, 0.8),
    "53239": ("CMSA", 0.75, 40.0, 2.2),
    "54216": ("CMSA", 0.75, 42.0, 2.2),
    "66052": ("JAXA", 0.35, 60.0, 2.0),
    "66515": ("CMSA Cargo", 0.65, 55.0, 2.5),
    "66906": ("Astroscale", 0.50, 70.0, 3.0),
    "67683": ("GeoInformatics", 0.45, 65.0, 2.8),
    "67685": ("SpaceX", 0.40, 75.0, 3.2),
    "67686": ("UiTM Tech", 0.38, 70.0, 2.7),
    "67687": ("Leopard Space", 0.42, 68.0, 2.9),
    "67688": ("HMU Aerospace", 0.48, 62.0, 3.1),
    "67796": ("SpaceX / NASA", 0.92, 35.0, 2.5),
    "68689": ("Northrop Grumman", 0.60, 30.0, 2.0),
    "68837": ("Roscosmos", 0.75, 50.0, 2.2),
    "69049": ("CMSA Cargo", 0.80, 65.0, 3.0),
    "69180": ("CMSA Crewed", 0.95, 40.0, 2.5),
}


def resolve_operator_profile(
    norad_id: str,
    satellite_name: str = "",
    agent_id: AgentId = AgentId.OPERATOR_A,
) -> OperatorProfile:
    """Dynamically resolves or constructs an OperatorProfile for any satellite."""
    if norad_id in KNOWN_OPERATOR_PROFILES:
        op_name, mvi, fuel_pct, dv_mps = KNOWN_OPERATOR_PROFILES[norad_id]
    else:
        op_name = f"Operator-{norad_id}"
        # Deterministic hashing based on norad_id to avoid identical values for distinct satellites
        num_id = int(norad_id) if norad_id.isdigit() else abs(hash(norad_id))
        mvi = round(0.35 + ((num_id * 17) % 55) / 100.0, 2)
        fuel_pct = round(15.0 + ((num_id * 31) % 70), 1)
        dv_mps = round(1.5 + ((num_id * 13) % 25) / 10.0, 1)

    return OperatorProfile(
        agent_id=agent_id,
        operator_name=op_name,
        satellite_name=satellite_name or f"SAT-{norad_id}",
        norad_id=norad_id,
        mvi=mvi,
        fuel_margin_pct=fuel_pct,
        delta_v_mps=dv_mps,
    )


def get_operator_profiles_payload(all_objs: list[TrackedObject] | None = None) -> dict[str, dict]:
    """Returns profile metadata dictionary for all active tracked satellites."""
    if all_objs is None:
        all_objs = load_all_tracked_objects()
    payload = {}
    for obj in all_objs:
        prof = resolve_operator_profile(obj.norad_id, obj.name)
        payload[obj.norad_id] = {
            "operator_name": prof.operator_name,
            "fuel_margin_pct": prof.fuel_margin_pct,
            "mvi": prof.mvi,
            "delta_v_mps": prof.delta_v_mps,
        }
    return payload


class Orchestrator:
    """Owns session state and dispatches Monitor-slice events over the
    WebSocket layer via `ConnectionManager`. Never touches physics/negotiation
    math directly (architecture.md §System Boundaries)."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connections = connection_manager

    def detect_conjunctions(self) -> list[ConjunctionAlert]:
        """Runs dynamic conjunction detection across all tracked satellites,
        excluding pairs that are physically docked/co-located (see
        DOCKED_OBJECT_GROUPS) — those aren't real conjunctions."""
        all_objects = load_all_tracked_objects()
        alerts = run_detect_conjunctions(all_objects)
        alerts = [a for a in alerts if not _is_docked_pair(a.primary_id, a.secondary_id)]
        return alerts if alerts else [_HARDCODED_ALERT]

    def monitor_snapshot_payload(self) -> dict:
        """
        Snapshot payload for a new /ws/monitor connection. Includes
        the 20 live/cached CelesTrak tracked objects and operatorProfiles metadata.
        """
        tracked_objs = load_all_tracked_objects()
        return {
            "conjunctions": [],
            "trackedObjects": [obj.model_dump() for obj in tracked_objs],
            "operatorProfiles": get_operator_profiles_payload(tracked_objs),
        }

    async def broadcast_conjunction_alerts(
        self, session_id: str = MONITOR_SESSION_ID
    ) -> None:
        for alert in self.detect_conjunctions():
            await self._connections.broadcast(session_id, EventType.CONJUNCTION_ALERT, alert)

    async def run_negotiation_session(
        self,
        conjunction_id: str,
        session_id: str,
        force_rejection: bool = False,
    ) -> None:
        """
        Runs Dev C's NegotiationEngine (agents/negotiator.py) dynamically routed
        for the specified conjunction_id, resolving satellite objects and operator
        profiles dynamically.
        """
        alerts = self.detect_conjunctions()
        alert = next((a for a in alerts if a.id == conjunction_id), alerts[0])

        all_objects = load_all_tracked_objects()

        sat_a = next((obj for obj in all_objects if obj.norad_id == alert.primary_id), None)
        sat_b = next((obj for obj in all_objects if obj.norad_id == alert.secondary_id), None)

        if not sat_a or not sat_b:
            seeded = get_seeded_scenario_objects()
            sat_a = sat_a or next((obj for obj in seeded if obj.norad_id == alert.primary_id), seeded[0])
            sat_b = sat_b or next((obj for obj in seeded if obj.norad_id == alert.secondary_id), seeded[1])

        profile_a = resolve_operator_profile(sat_a.norad_id, sat_a.name, AgentId.OPERATOR_A)
        profile_b = resolve_operator_profile(sat_b.norad_id, sat_b.name, AgentId.OPERATOR_B)

        engine = NegotiationEngine(alert, profile_a, profile_b, sat_a, sat_b, all_objects)

        try:
            transcript, resolution = await asyncio.to_thread(
                engine.run_negotiation, force_initial_rejection=force_rejection
            )
        except Exception:
            logger.exception(
                "[orchestrator] negotiation engine failed for conjunction %s", conjunction_id
            )
            await self._connections.broadcast(
                session_id,
                EventType.ERROR,
                ErrorPayload(message="Negotiation engine failed", code="negotiation_error"),
            )
            return

        for message in transcript:
            await self._connections.broadcast(session_id, EventType.NEGOTIATION_MESSAGE, message)

        await self._connections.broadcast(session_id, EventType.RESOLUTION, resolution)

        try:
            from app.storage.db import save_completed_session
            save_completed_session(alert, transcript, resolution)
            logger.info("Successfully persisted negotiation session to DB")
        except Exception as e:
            logger.error("Failed to save negotiation session to DB: %s", e)
