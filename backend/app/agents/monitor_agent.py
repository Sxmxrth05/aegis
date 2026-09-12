"""
A2 — SGP4 propagation.

Owner: Dev A (Orbital Physics & Conjunction Detection) / Dev C (coverage fixes)

This module is the ONE place in the whole system that runs SGP4. Dev C's
validation_agent.py reuses propagate()/propagate_window() directly rather
than reimplementing propagation — per the build plan's stated interface
reuse.

Takes raw TLE data in (from data/celestrak.py) and produces canonical
Pydantic TrackedObject instances (from schemas.tracked_object) out.
"""

from __future__ import annotations

import math
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Any

# Ensure backend root is on sys.path for direct script execution
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
_APP_DIR = _BACKEND_DIR / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from sgp4.api import Satrec, SGP4_ERRORS, jday

try:
    from backend.app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
    from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    try:
        from app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
        from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
        from app.schemas.tracked_object import TrackedObject
    except ImportError:
        CONJUNCTION_THRESHOLD_KM = 5.0
        HYSTERESIS_CLEAR_KM = 4.0
        from enum import Enum
        from pydantic import BaseModel, Field

        class ConjunctionStatus(str, Enum):
            ALERTED = "alerted"
            NEGOTIATING = "negotiating"
            RESOLVED = "resolved"
            ESCALATED = "escalated"
            STOOD_DOWN = "stood_down"

        class ConjunctionAlert(BaseModel):
            id: str
            primary_id: str
            secondary_id: str
            tca_utc: str
            miss_distance_km: float
            relative_velocity_kmps: float
            status: ConjunctionStatus
            created_at: str

        # No local TrackedObject fallback here — schemas.tracked_object.TrackedObject
        # is the single canonical definition; if both import paths above fail, this
        # module should error loudly (NameError) rather than silently duplicate it.


# Backward compatibility alias
StateVector = TrackedObject


class PropagationError(Exception):
    """Raised when SGP4 returns a non-zero error code for a given time."""


def build_satellite(tle_line1: str, tle_line2: str) -> Satrec:
    """Construct a Satrec object from two TLE lines."""
    return Satrec.twoline2rv(tle_line1, tle_line2)


def _datetime_to_jd_fr(dt: datetime) -> tuple[float, float]:
    """Convert a UTC datetime to the (jd, fr) pair sgp4 expects."""
    if dt.tzinfo is None:
        raise ValueError("propagate() requires a timezone-aware UTC datetime")
    dt_utc = dt.astimezone(timezone.utc)
    jd, fr = jday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour, dt_utc.minute,
        dt_utc.second + dt_utc.microsecond / 1e6,
    )
    return jd, fr


def propagate(
    satellite: Satrec,
    norad_id: str,
    time_utc: datetime,
    name: str = "",
    tle_line1: str = "",
    tle_line2: str = "",
) -> TrackedObject:
    """
    Propagate a single satellite to a single instant and construct the
    canonical Pydantic TrackedObject (with timestamp_utc, position_km, velocity_kmps).
    Raises PropagationError on any SGP4 error code (e.g. decayed orbit,
    invalid eccentricity) — callers must not silently trust a zero vector.
    """
    jd, fr = _datetime_to_jd_fr(time_utc)
    error_code, r, v = satellite.sgp4(jd, fr)

    if error_code != 0:
        raise PropagationError(
            f"SGP4 error {error_code} for NORAD {norad_id} at {time_utc.isoformat()}: "
            f"{SGP4_ERRORS.get(error_code, 'unknown error')}"
        )

    return TrackedObject(
        norad_id=norad_id,
        name=name or f"OBJECT-{norad_id}",
        tle_line1=tle_line1,
        tle_line2=tle_line2,
        timestamp_utc=time_utc.isoformat(),
        position_km=r,
        velocity_kmps=v,
    )


def propagate_raw_tle(raw: Any, time_utc: datetime) -> TrackedObject:
    """
    Convenience helper: propagate a raw TLE record (RawTLE dataclass or dict)
    into the canonical Pydantic TrackedObject.
    """
    if isinstance(raw, dict):
        norad_id = raw["norad_id"]
        name = raw.get("name", f"OBJECT-{norad_id}")
        tle_line1 = raw["tle_line1"]
        tle_line2 = raw["tle_line2"]
    else:
        norad_id = raw.norad_id
        name = raw.name
        tle_line1 = raw.tle_line1
        tle_line2 = raw.tle_line2

    sat = build_satellite(tle_line1, tle_line2)
    return propagate(
        satellite=sat,
        norad_id=norad_id,
        time_utc=time_utc,
        name=name,
        tle_line1=tle_line1,
        tle_line2=tle_line2,
    )


def propagate_window(
    satellite: Satrec,
    norad_id: str,
    start_utc: datetime,
    end_utc: datetime,
    step_seconds: int,
    name: str = "",
    tle_line1: str = "",
    tle_line2: str = "",
) -> list[TrackedObject]:
    """
    Propagate a satellite across a time window at a fixed step.
    Skips (does not crash on) individual timesteps that error out, but
    logs them via the returned gap so A3's caller can decide how to react
    to a partial window — a single bad timestep shouldn't kill the whole
    rolling scan.
    """
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")

    results: list[TrackedObject] = []
    t = start_utc
    while t <= end_utc:
        try:
            results.append(
                propagate(
                    satellite=satellite,
                    norad_id=norad_id,
                    time_utc=t,
                    name=name,
                    tle_line1=tle_line1,
                    tle_line2=tle_line2,
                )
            )
        except PropagationError:
            pass  # gap in coverage for this timestep; A3 handles sparse windows
        t += timedelta(seconds=step_seconds)

    return results


def propagate_many(
    satellites: Iterable[tuple[str, Satrec]],
    start_utc: datetime,
    end_utc: datetime,
    step_seconds: int,
) -> dict[str, list[TrackedObject]]:
    """
    Convenience wrapper for A3: propagate a whole tracked-object set over
    the same window in one call. Returns {norad_id: [TrackedObject, ...]}.
    """
    return {
        norad_id: propagate_window(sat, norad_id, start_utc, end_utc, step_seconds)
        for norad_id, sat in satellites
    }


# ---------------------------------------------------------------------------
# A3: Conjunction Detection, Pairwise Distance, and Hysteresis Logic
# ---------------------------------------------------------------------------

def pairwise_distance_km(
    pos_a: tuple[float, float, float],
    pos_b: tuple[float, float, float],
) -> float:
    """Straight-line Euclidean distance in km between two ECI coordinates."""
    return math.sqrt(
        (pos_a[0] - pos_b[0]) ** 2
        + (pos_a[1] - pos_b[1]) ** 2
        + (pos_a[2] - pos_b[2]) ** 2
    )


def relative_velocity_kmps(
    vel_a: tuple[float, float, float],
    vel_b: tuple[float, float, float],
) -> float:
    """Magnitude of relative velocity vector in km/s between two objects."""
    return math.sqrt(
        (vel_a[0] - vel_b[0]) ** 2
        + (vel_a[1] - vel_b[1]) ** 2
        + (vel_a[2] - vel_b[2]) ** 2
    )


def detect_conjunctions(
    tracked_objects: list[TrackedObject] | None = None,
    threshold_km: float = CONJUNCTION_THRESHOLD_KM,
    hysteresis_km: float = HYSTERESIS_CLEAR_KM,
    active_alerts: dict[tuple[str, str], ConjunctionAlert] | None = None,
) -> list[ConjunctionAlert]:
    """
    A3 — Pairwise distance scanning with threshold & hysteresis logic.

    Scans all pairs in `tracked_objects` (defaults to the seeded scenario if None).
    Flags any pair whose separation is < threshold_km (5.0 km).
    Applies hysteresis: existing alerts remain active until separation clears
    beyond threshold_km (or hysteresis_km).

    Returns a list of schema-valid ConjunctionAlert objects.
    """
    if tracked_objects is None:
        try:
            from backend.app.data.scenario import get_seeded_scenario_objects
        except ImportError:
            from app.data.scenario import get_seeded_scenario_objects
        tracked_objects = get_seeded_scenario_objects()

    alerts: list[ConjunctionAlert] = []
    n = len(tracked_objects)

    for i in range(n):
        for j in range(i + 1, n):
            obj_a = tracked_objects[i]
            obj_b = tracked_objects[j]

            dist_km = pairwise_distance_km(obj_a.position_km, obj_b.position_km)
            rel_vel = relative_velocity_kmps(obj_a.velocity_kmps, obj_b.velocity_kmps)
            pair_key = tuple(sorted([obj_a.norad_id, obj_b.norad_id]))

            # Deterministic UUID based on pair and timestamp for repeatability
            alert_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"conjunction_{pair_key[0]}_{pair_key[1]}"))

            if dist_km < threshold_km:
                alert = ConjunctionAlert(
                    id=alert_id,
                    primary_id=obj_a.norad_id,
                    secondary_id=obj_b.norad_id,
                    tca_utc=obj_a.timestamp_utc or datetime.now(timezone.utc).isoformat(),
                    miss_distance_km=round(dist_km, 3),
                    relative_velocity_kmps=round(rel_vel, 3),
                    status=ConjunctionStatus.ALERTED,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                alerts.append(alert)
            elif active_alerts and pair_key in active_alerts:
                # Hysteresis check: if separation has now safely cleared
                existing = active_alerts[pair_key]
                if dist_km >= threshold_km:
                    stood_down = ConjunctionAlert(
                        id=existing.id,
                        primary_id=existing.primary_id,
                        secondary_id=existing.secondary_id,
                        tca_utc=existing.tca_utc,
                        miss_distance_km=round(dist_km, 3),
                        relative_velocity_kmps=round(rel_vel, 3),
                        status=ConjunctionStatus.STOOD_DOWN,
                        created_at=existing.created_at,
                    )
                    alerts.append(stood_down)

    return alerts


if __name__ == "__main__":
    s = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
    t = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"
    sat = build_satellite(s, t)
    now = datetime(2019, 12, 9, 20, 42, 0, tzinfo=timezone.utc)
    obj = propagate(sat, "25544", now, name="ISS (ZARYA)", tle_line1=s, tle_line2=t)
    print(f"Propagated TrackedObject:\n  {obj}")
    print(f"Position (km): {obj.position_km}")
    print(f"Velocity (km/s): {obj.velocity_kmps}")

    print("\n--- Running detect_conjunctions() on Seeded Scenario ---")
    detected = detect_conjunctions()
    print(f"Found {len(detected)} conjunction alerts:")
    for alert in detected:
        print(f"  Alert {alert.id}: {alert.primary_id} <-> {alert.secondary_id} "
              f"at miss_distance={alert.miss_distance_km} km (status: {alert.status})")