"""
A3 — Seeded Conjunction Scenario & Scenario Generator.

Owner: Dev A (Orbital Physics & Conjunction Detection) / Dev C (coverage)

Provides a reproducible, offline-verifiable scenario that guarantees ≥1
sub-threshold conjunction alert (< CONJUNCTION_THRESHOLD_KM = 5.0 km).
Used by monitor_agent.py, orchestrator.py, and the frontend demo feed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from backend.app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
    from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    from app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
    from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from app.schemas.tracked_object import TrackedObject


FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Primary conjunction pair for the demo
PRIMARY_NORAD_ID = "25544"   # ISS (ZARYA)
SECONDARY_NORAD_ID = "48274" # CSS (TIANHE) / Debris counterpart
SCENARIO_TCA_UTC = "2026-01-14T06:12:00Z"
SCENARIO_MISS_DISTANCE_KM = 3.2
SCENARIO_RELATIVE_VELOCITY_KMPS = 7.5

# Seeded tracked objects at T_approach
_BASE_OBJECTS: list[dict] = [
    {
        "norad_id": "25544",
        "name": "ISS (ZARYA)",
        "tle_line1": "1 25544U 98067A   26014.25000000  .00016717  00000-0  10270-3 0  9000",
        "tle_line2": "2 25544  51.6400 208.9163 0006317  69.9862  25.2906 15.50377579100000",
        "timestamp_utc": "2026-01-14T06:12:00.000Z",
        "position_km": (2577.608, -3366.514, 5294.249),
        "velocity_kmps": (6.472113, 4.076564, -0.554895),
    },
    {
        "norad_id": "48274",
        "name": "CSS (TIANHE)",
        "tle_line1": "1 48274U 21035A   26014.30000000  .00021000  00000-0  22000-3 0  9001",
        "tle_line2": "2 48274  41.4700 120.5000 0002000  90.0000 270.1000 15.61000000100000",
        "timestamp_utc": "2026-01-14T06:12:00.000Z",
        # Position placed precisely 3.20 km away from ISS to satisfy A3 guarantee
        # Δ = (2.0, 2.0, 1.50) km -> sqrt(4 + 4 + 2.25) = 3.2015 km
        "position_km": (2577.608 + 2.0, -3366.514 + 2.0, 5294.249 + 1.5),
        "velocity_kmps": (-1.027887, 4.076564, 4.513271),
    },
    {
        "norad_id": "44713",
        "name": "STARLINK-1007",
        "tle_line1": "1 44713U 19074A   26014.40000000  .00002000  00000-0  15000-3 0  9002",
        "tle_line2": "2 44713  53.0000  60.0000 0001200  80.0000 280.1000 15.06000000100000",
        "timestamp_utc": "2026-01-14T06:12:00.000Z",
        "position_km": (3419.274, -2418.406, -5524.09),
        "velocity_kmps": (3.952255, 6.453008, -0.378761),
    },
    {
        "norad_id": "36086",
        "name": "POISK",
        "tle_line1": "1 36086U 09049A   26014.20000000  .00010000  00000-0  90000-4 0  9003",
        "tle_line2": "2 36086  51.6400 210.0000 0006000  75.0000  20.0000 15.50000000100000",
        "timestamp_utc": "2026-01-14T06:12:00.000Z",
        "position_km": (-5213.496, -4157.61, 1290.823),
        "velocity_kmps": (3.911567, -3.075879, 5.830827),
    },
    {
        "norad_id": "68689",
        "name": "CYGNUS NG-24",
        "tle_line1": "1 68689U 24160A   26014.10000000  .00030000  00000-0  35000-3 0  9004",
        "tle_line2": "2 68689  51.6400 205.0000 0005500  60.0000  35.0000 15.51000000100000",
        "timestamp_utc": "2026-01-14T06:12:00.000Z",
        "position_km": (4236.171, 4444.603, -2919.122),
        "velocity_kmps": (-5.451392, 1.903278, -5.025646),
    },
]


def get_seeded_scenario_objects(
    tca_utc: str = SCENARIO_TCA_UTC,
) -> list[TrackedObject]:
    """
    Returns the seeded tracked objects for the scenario.
    Guarantees that ISS (25544) and CSS (48274) are separated by exactly
    3.20 km (< CONJUNCTION_THRESHOLD_KM = 5.0 km).
    """
    objects = []
    for item in _BASE_OBJECTS:
        obj_dict = dict(item)
        obj_dict["timestamp_utc"] = tca_utc
        objects.append(TrackedObject(**obj_dict))
    return objects


def get_seeded_conjunction_alert(
    alert_id: str = "9f1c1e2a-4b3d-4a5e-9c6f-1a2b3c4d5e6f",
    tca_utc: str = SCENARIO_TCA_UTC,
    status: ConjunctionStatus = ConjunctionStatus.ALERTED,
) -> ConjunctionAlert:
    """
    Returns the canonical sub-threshold ConjunctionAlert guaranteed by A3.
    """
    return ConjunctionAlert(
        id=alert_id,
        primary_id=PRIMARY_NORAD_ID,
        secondary_id=SECONDARY_NORAD_ID,
        tca_utc=tca_utc,
        miss_distance_km=SCENARIO_MISS_DISTANCE_KM,
        relative_velocity_kmps=SCENARIO_RELATIVE_VELOCITY_KMPS,
        status=status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
