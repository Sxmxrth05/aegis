"""TrackedObject — a single satellite's state, sourced from a TLE and/or
its SGP4-propagated position at a point in time.

Not a DB-persisted table in architecture.md's schema; this is the shared
in-memory/wire shape produced by Dev A's `propagate()` and consumed by the
WebSocket snapshot payload and the frontend globe.
"""

from pydantic import BaseModel, Field


class TrackedObject(BaseModel):
    norad_id: str = Field(..., description="NORAD catalog number")
    name: str
    tle_line1: str
    tle_line2: str

    timestamp_utc: str = Field(..., description="ISO timestamp (UTC) of this state")

    position_km: tuple[float, float, float] = Field(
        ..., description="ECI position (x, y, z) in kilometers"
    )
    velocity_kmps: tuple[float, float, float] = Field(
        ..., description="ECI velocity (x, y, z) in km/s"
    )
