"""
Offline sanity check for celestrak.py's parsing + caching logic, using the
real TLE sample you already pulled from CelesTrak by hand. This does NOT
hit the network — it exercises parse_tle_text() / write_cache() / read_cache()
directly so you can verify the logic before relying on a live connection.
"""

from datetime import datetime, timezone
from pathlib import Path

try:
    from backend.app.data.celestrak import parse_tle_text, write_cache, read_cache, LOCKED_OBJECTS
except ImportError:
    try:
        from app.data.celestrak import parse_tle_text, write_cache, read_cache, LOCKED_OBJECTS
    except ImportError:
        from celestrak import parse_tle_text, write_cache, read_cache, LOCKED_OBJECTS

# The exact text you pulled live from CelesTrak's `stations` group.
SAMPLE_TLE_TEXT = """ISS (ZARYA)             
1 25544U 98067A   26254.62728023  .00005127  00000+0  10088-3 0  9993
2 25544  51.6304 232.2787 0004958 129.1564 230.9865 15.49080967585152
POISK                   
1 36086U 09060A   26254.62728023  .00005127  00000+0  10088-3 0  9991
2 36086  51.6304 232.2787 0004958 129.1564 230.9865 15.49080967585975
CSS (TIANHE)            
1 48274U 21035A   26254.89562246  .00017425  00000+0  21444-3 0  9993
2 48274  41.4684 155.5829 0002605 272.3198  87.7342 15.598303543067  1
"""

TEST_CACHE_PATH = Path(__file__).parent / "cache" / "test_tracked_objects.json"


def run():
    fetched_at = datetime(2026, 9, 12, tzinfo=timezone.utc)

    print("1. Parsing sample TLE text...")
    objects = parse_tle_text(SAMPLE_TLE_TEXT, fetched_at=fetched_at)
    assert len(objects) == 3, f"expected 3 parsed objects, got {len(objects)}"
    for o in objects:
        assert o.norad_id in LOCKED_OBJECTS
        print(f"   OK  {o.norad_id}  {o.name:<20} epoch={o.epoch_utc}  stale={o.is_stale}")

    print("\n2. Writing to test cache...")
    write_cache(objects, cache_path=TEST_CACHE_PATH)
    assert TEST_CACHE_PATH.exists()
    print(f"   OK  wrote {TEST_CACHE_PATH}")

    print("\n3. Reading back from cache...")
    reloaded = read_cache(cache_path=TEST_CACHE_PATH)
    assert len(reloaded) == 3
    assert {o.norad_id for o in reloaded} == {o.norad_id for o in objects}
    print(f"   OK  read back {len(reloaded)} objects, IDs match")

    print("\n4. Checking known values round-tripped correctly...")
    iss = next(o for o in reloaded if o.norad_id == "25544")
    assert iss.name == "ISS (ZARYA)"
    assert iss.is_active is True
    assert iss.tle_line1.startswith("1 25544U")
    print("   OK  ISS (ZARYA) fields correct after round-trip")

    print("\nAll offline checks passed.")
    TEST_CACHE_PATH.unlink()  # clean up test artifact


def test_celestrak_offline():
    run()


if __name__ == "__main__":
    run()