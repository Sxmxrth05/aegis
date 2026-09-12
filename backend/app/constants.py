"""Shared demo-relevant thresholds and limits.

Single-owner file (Dev B, per code-standards.md §File & Folder Ownership).
Kept at the app root — not inside agents/ — since that directory is owned by
Dev A/Dev C; agents import these constants rather than redefining them.
"""

# Below this separation, a pair of tracked objects is flagged as a conjunction.
CONJUNCTION_THRESHOLD_KM = 5.0

# Above this separation, a previously alerted conjunction is cleared.
# Kept below CONJUNCTION_THRESHOLD_KM to avoid alert flapping at the boundary.
HYSTERESIS_CLEAR_KM = 4.0

# Negotiation rounds are capped; non-convergence escalates deterministically
# rather than looping forever (architecture.md invariant 4).
MAX_NEGOTIATION_ROUNDS = 3

# How far ahead the validation agent re-propagates to check a proposed
# maneuver for secondary risk.
VALIDATION_LOOKAHEAD_HOURS = 6
