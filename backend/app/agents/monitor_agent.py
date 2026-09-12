"""
A2 — SGP4 propagation.

Owner: Dev A (Orbital Physics & Conjunction Detection)

This module is the ONE place in the whole system that runs SGP4. Dev C's
validation_agent.py reuses propagate()/propagate_window() directly rather
than reimplementing propagation — per the build plan's stated interface
reuse.

No I/O here: this module only does math. It takes TrackedObject-shaped
data in (from data/celestrak.py) and returns plain Python data out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sgp4.api import Satrec, SGP4_ERRORS, jday


class PropagationError(Exception):
    """Raised when SGP4 returns a non-zero error code for a given time."""


@dataclass(frozen=True)
class StateVector:
    """Position and velocity at one instant, in the TEME frame (per sgp4)."""
    norad_id: str
    time_utc: str          # ISO 8601
    position_km: tuple[float, float, float]
    velocity_kmps: tuple[float, float, float]


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


def propagate(satellite: Satrec, norad_id: str, time_utc: datetime) -> StateVector:
    """
    Propagate a single satellite to a single instant.
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

    return StateVector(
        norad_id=norad_id,
        time_utc=time_utc.isoformat(),
        position_km=r,
        velocity_kmps=v,
    )


def propagate_window(
    satellite: Satrec,
    norad_id: str,
    start_utc: datetime,
    end_utc: datetime,
    step_seconds: int,
) -> list[StateVector]:
    """
    Propagate a satellite across a time window at a fixed step.
    Skips (does not crash on) individual timesteps that error out, but
    logs them via the returned gap so A3's caller can decide how to react
    to a partial window — a single bad timestep shouldn't kill the whole
    rolling scan.
    """
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")

    results: list[StateVector] = []
    t = start_utc
    while t <= end_utc:
        try:
            results.append(propagate(satellite, norad_id, t))
        except PropagationError:
            pass  # gap in coverage for this timestep; A3 handles sparse windows
        t += timedelta(seconds=step_seconds)

    return results


def propagate_many(
    satellites: Iterable[tuple[str, Satrec]],
    start_utc: datetime,
    end_utc: datetime,
    step_seconds: int,
) -> dict[str, list[StateVector]]:
    """
    Convenience wrapper for A3: propagate a whole tracked-object set over
    the same window in one call. Returns {norad_id: [StateVector, ...]}.
    """
    return {
        norad_id: propagate_window(sat, norad_id, start_utc, end_utc, step_seconds)
        for norad_id, sat in satellites
    }


if __name__ == "__main__":
    # Quick manual smoke test using ISS's real TLE — not the validation
    # test (see test_monitor_agent_validation.py for the accuracy check
    # against a known reference position).
    s = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
    t = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"
    sat = build_satellite(s, t)
    now = datetime(2019, 12, 9, 20, 42, 0, tzinfo=timezone.utc)
    state = propagate(sat, "25544", now)
    print(f"Position (km): {state.position_km}")
    print(f"Velocity (km/s): {state.velocity_kmps}")