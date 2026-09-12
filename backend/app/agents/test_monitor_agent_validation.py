"""
A2 completion criterion: "validated against a known satellite's expected
position." This test uses the exact worked example from the sgp4 library's
own documentation (ISS, 2019-12-09 20:42:00 UTC) — a reference computed by
the standard Vallado C++ implementation, which sgp4's own test suite
confirms agrees to within 0.1mm. That makes it a trustworthy independent
check, not something we invented ourselves.
"""

from datetime import datetime, timezone

from monitor_agent import build_satellite, propagate

# Reference TLE and expected output, taken directly from the sgp4 package's
# published documentation (pypi.org/project/sgp4).
TLE_LINE1 = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
TLE_LINE2 = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"

EXPECTED_POSITION_KM = (-6088.92, -936.13, -2866.44)
EXPECTED_VELOCITY_KMPS = (-1.525, -5.538, 5.068)

# Loose enough to allow for the doc's truncated reference digits, tight
# enough to catch a real propagation bug (wrong satellite, wrong frame,
# wrong time conversion, etc.)
TOLERANCE_KM = 0.5
TOLERANCE_KMPS = 0.01


def _vectors_close(actual, expected, tolerance):
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def run():
    print("Validating monitor_agent.propagate() against known ISS reference...")

    satellite = build_satellite(TLE_LINE1, TLE_LINE2)
    reference_time = datetime(2019, 12, 9, 20, 42, 0, tzinfo=timezone.utc)

    state = propagate(satellite, "25544", reference_time)

    print(f"  Computed position (km): {state.position_km}")
    print(f"  Expected position (km): {EXPECTED_POSITION_KM}")
    assert _vectors_close(state.position_km, EXPECTED_POSITION_KM, TOLERANCE_KM), (
        "Position mismatch exceeds tolerance — propagation logic is wrong"
    )
    print("  OK  position within tolerance")

    print(f"  Computed velocity (km/s): {state.velocity_kmps}")
    print(f"  Expected velocity (km/s): {EXPECTED_VELOCITY_KMPS}")
    assert _vectors_close(state.velocity_kmps, EXPECTED_VELOCITY_KMPS, TOLERANCE_KMPS), (
        "Velocity mismatch exceeds tolerance — propagation logic is wrong"
    )
    print("  OK  velocity within tolerance")

    print("\nA2 validation passed: propagation matches the known reference.")


if __name__ == "__main__":
    run()