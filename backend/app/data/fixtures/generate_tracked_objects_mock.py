"""
Generates the Phase 0 mock fixture for Dev D: a static JSON file matching
Dev B's TrackedObject schema exactly, populated with REAL propagated
positions from your actual cached TLE data (not invented numbers).

Run this after A1 (celestrak.py) has written a fresh cache/tracked_objects.json.

Output: backend/app/data/fixtures/tracked_objects_mock.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))       # backend/app/data
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))  # backend/app/agents

from celestrak import read_cache, CACHE_PATH
from monitor_agent import build_satellite, propagate, PropagationError

OUTPUT_PATH = Path(__file__).parent / "tracked_objects_mock.json"


def generate():
    cached_objects = read_cache(CACHE_PATH)
    now = datetime.now(timezone.utc)

    fixture = []
    skipped = []

    for obj in cached_objects:
        try:
            satellite = build_satellite(obj.tle_line1, obj.tle_line2)
            state = propagate(satellite, obj.norad_id, now)
        except PropagationError as e:
            skipped.append((obj.norad_id, str(e)))
            continue

        # Matches Dev B's TrackedObject schema field-for-field.
        fixture.append({
            "norad_id": obj.norad_id,
            "name": obj.name,
            "tle_line1": obj.tle_line1,
            "tle_line2": obj.tle_line2,
            "timestamp_utc": state.time_utc,
            "position_km": list(state.position_km),
            "velocity_kmps": list(state.velocity_kmps),
        })

    OUTPUT_PATH.write_text(json.dumps(fixture, indent=2))

    print(f"Wrote {len(fixture)} real propagated objects to {OUTPUT_PATH}")
    if skipped:
        print(f"Skipped {len(skipped)} objects due to propagation errors:")
        for norad_id, err in skipped:
            print(f"  {norad_id}: {err}")


if __name__ == "__main__":
    generate()