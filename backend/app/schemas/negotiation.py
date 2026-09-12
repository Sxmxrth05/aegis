"""NegotiationMessage and Resolution — mirror architecture.md's
`negotiation_messages` and `resolutions` tables exactly.
"""

from enum import Enum

from pydantic import BaseModel, Field


class AgentId(str, Enum):
    OPERATOR_A = "operator_A"
    OPERATOR_B = "operator_B"
    VALIDATION = "validation"


class ProposedAction(str, Enum):
    MANEUVER = "maneuver"
    STAND_DOWN = "stand_down"
    REJECT = "reject"
    APPROVE = "approve"


class NegotiationMessage(BaseModel):
    id: str = Field(..., description="UUID")
    conjunction_id: str = Field(..., description="FK -> conjunctions.id")
    agent_id: AgentId
    round: int
    yield_score: float | None = Field(
        default=None, description="Nullable for validation-agent rows"
    )
    justification_text: str
    proposed_action: ProposedAction
    created_at: str = Field(..., description="ISO timestamp")


class ResolutionStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_NO_ACTION = "approved_no_action"
    NO_SAFE_MANEUVER_FOUND = "no_safe_maneuver_found"


class Resolution(BaseModel):
    id: str = Field(..., description="UUID")
    conjunction_id: str = Field(..., description="FK -> conjunctions.id")
    maneuvering_agent: str = Field(..., description="Which satellite moves")
    maneuver_type: str
    delta_v_mps: float
    execution_time_utc: str = Field(..., description="ISO timestamp")
    expected_min_distance_km: float
    residual_risk: float
    rationale_text: str
    status: ResolutionStatus
