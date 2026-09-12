"""
A3 standalone verification test:
1. Validates seeded scenario in data/scenario.py
2. Validates detect_conjunctions() returns schema-valid ConjunctionAlert objects
3. Confirms scenario reliably yields >=1 alert below threshold (< 5.0 km)
4. Verifies hysteresis logic when objects clear
5. Verifies Phase 0 fixtures (conjunction_alert.json, tracked_objects.json)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
_APP_DIR = _BACKEND_DIR / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from backend.app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
    from backend.app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from backend.app.schemas.tracked_object import TrackedObject
    from backend.app.agents.monitor_agent import (
        detect_conjunctions,
        pairwise_distance_km,
        relative_velocity_kmps,
    )
    from backend.app.data.scenario import (
        get_seeded_scenario_objects,
        get_seeded_conjunction_alert,
        PRIMARY_NORAD_ID,
        SECONDARY_NORAD_ID,
    )
except ImportError:
    from app.constants import CONJUNCTION_THRESHOLD_KM, HYSTERESIS_CLEAR_KM
    from app.schemas.conjunction import ConjunctionAlert, ConjunctionStatus
    from app.schemas.tracked_object import TrackedObject
    from app.agents.monitor_agent import (
        detect_conjunctions,
        pairwise_distance_km,
        relative_velocity_kmps,
    )
    from app.data.scenario import (
        get_seeded_scenario_objects,
        get_seeded_conjunction_alert,
        PRIMARY_NORAD_ID,
        SECONDARY_NORAD_ID,
    )


def test_scenario_conjunction():
    print("=" * 60)
    print("A3 Verification: Conjunction Detection & Seeded Scenario")
    print("=" * 60)

    # 1. Load seeded scenario objects
    objects = get_seeded_scenario_objects()
    assert len(objects) >= 2, "Expected at least 2 scenario objects"
    print(f"[PASS] Loaded {len(objects)} seeded TrackedObjects")

    # 2. Run detect_conjunctions()
    alerts = detect_conjunctions(objects)
    assert len(alerts) >= 1, "A3 criterion failed: expected >= 1 conjunction alert"
    print(f"[PASS] detect_conjunctions() returned {len(alerts)} alert(s)")

    # 3. Check schema validity and sub-threshold condition
    alert = alerts[0]
    assert isinstance(alert, ConjunctionAlert), "Alert must be a Pydantic ConjunctionAlert"
    assert alert.status == ConjunctionStatus.ALERTED
    assert alert.primary_id in (PRIMARY_NORAD_ID, SECONDARY_NORAD_ID)
    assert alert.secondary_id in (PRIMARY_NORAD_ID, SECONDARY_NORAD_ID)
    assert alert.miss_distance_km < CONJUNCTION_THRESHOLD_KM, (
        f"Miss distance {alert.miss_distance_km} must be < {CONJUNCTION_THRESHOLD_KM} km"
    )
    print(f"[PASS] Alert confirmed sub-threshold: {alert.primary_id} <-> {alert.secondary_id} "
          f"miss_distance={alert.miss_distance_km:.3f} km (threshold: {CONJUNCTION_THRESHOLD_KM} km)")

    # 4. Check math functions
    obj_a = next(o for o in objects if o.norad_id == PRIMARY_NORAD_ID)
    obj_b = next(o for o in objects if o.norad_id == SECONDARY_NORAD_ID)
    dist = pairwise_distance_km(obj_a.position_km, obj_b.position_km)
    rel_v = relative_velocity_kmps(obj_a.velocity_kmps, obj_b.velocity_kmps)
    assert abs(dist - alert.miss_distance_km) < 0.01
    print(f"[PASS] Pairwise math verified: dist={dist:.3f} km, rel_vel={rel_v:.3f} km/s")

    # 5. Check hysteresis logic (standing down when separation clears)
    # Simulate a separated state for obj_b (> 5.0 km)
    separated_obj_b = TrackedObject(
        norad_id=obj_b.norad_id,
        name=obj_b.name,
        tle_line1=obj_b.tle_line1,
        tle_line2=obj_b.tle_line2,
        timestamp_utc=obj_b.timestamp_utc,
        position_km=(obj_a.position_km[0] + 10.0, obj_a.position_km[1], obj_a.position_km[2]),
        velocity_kmps=obj_b.velocity_kmps,
    )
    pair_key = tuple(sorted([obj_a.norad_id, obj_b.norad_id]))
    active_alerts = {pair_key: alert}
    updated_alerts = detect_conjunctions([obj_a, separated_obj_b], active_alerts=active_alerts)
    stood_down = [a for a in updated_alerts if a.status == ConjunctionStatus.STOOD_DOWN]
    assert len(stood_down) == 1, "Expected alert to transition to STOOD_DOWN"
    print(f"[PASS] Hysteresis verified: alert transitioned to {stood_down[0].status}")

    # 6. Check Phase 0 fixtures on disk
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    alert_fixture_path = fixtures_dir / "conjunction_alert.json"
    assert alert_fixture_path.exists(), "conjunction_alert.json fixture missing"
    alert_data = json.loads(alert_fixture_path.read_text())
    parsed_alert = ConjunctionAlert(**alert_data)
    assert parsed_alert.miss_distance_km < CONJUNCTION_THRESHOLD_KM
    print("[PASS] Phase 0 fixture conjunction_alert.json is schema-valid")

    obj_fixture_path = fixtures_dir / "tracked_objects.json"
    assert obj_fixture_path.exists(), "tracked_objects.json fixture missing"
    objs_data = json.loads(obj_fixture_path.read_text())
    parsed_objs = [TrackedObject(**item) for item in objs_data]
    assert len(parsed_objs) == 5
    print("[PASS] Phase 0 fixture tracked_objects.json has 5 schema-valid objects")

    print("\n" + "=" * 60)
    print("ALL A3 COMPLETION CRITERIA SATISFIED (OFFLINE VERIFIED)")
    print("=" * 60)


if __name__ == "__main__":
    test_scenario_conjunction()
