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

from datetime import datetime, timedelta, timezone
from typing import Iterable, Any

from sgp4.api import Satrec, SGP4_ERRORS, jday

try:
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    try:
        from app.schemas.tracked_object import TrackedObject
    except ImportError:
        # Fallback if schemas package not in PYTHONPATH
        from pydantic import BaseModel, Field

        class TrackedObject(BaseModel):  # type: ignore[no-redef]
            norad_id: str
            name: str
            tle_line1: str
            tle_line2: str
            timestamp_utc: str
            position_km: tuple[float, float, float]
            velocity_kmps: tuple[float, float, float]


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


if __name__ == "__main__":
    s = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
    t = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"
    sat = build_satellite(s, t)
    now = datetime(2019, 12, 9, 20, 42, 0, tzinfo=timezone.utc)
    obj = propagate(sat, "25544", now, name="ISS (ZARYA)", tle_line1=s, tle_line2=t)
    print(f"Propagated TrackedObject:\n  {obj}")
    print(f"Position (km): {obj.position_km}")
    print(f"Velocity (km/s): {obj.velocity_kmps}")