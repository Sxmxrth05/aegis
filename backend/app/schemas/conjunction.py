"""ConjunctionAlert — mirrors architecture.md's `conjunctions` table exactly."""

from enum import Enum

from pydantic import BaseModel, Field


class ConjunctionStatus(str, Enum):
    ALERTED = "alerted"
    NEGOTIATING = "negotiating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    STOOD_DOWN = "stood_down"


class ConjunctionAlert(BaseModel):
    id: str = Field(..., description="UUID")
    primary_id: str = Field(..., description="NORAD catalog number")
    secondary_id: str = Field(..., description="NORAD catalog number")
    tca_utc: str = Field(..., description="ISO timestamp, time of closest approach")
    miss_distance_km: float
    relative_velocity_kmps: float
    status: ConjunctionStatus
    created_at: str = Field(..., description="ISO timestamp")
