import random

import pytest
from factory import ev

from dropcurve.hotspots import find_hotspots
from dropcurve.views import build


def listeners(n, cliff_at=None, cliff_share=0.0, seed=0):
    """Steady trickle of leavers, plus an optional cliff at one point."""
    rng = random.Random(seed)
    events = []
    for i in range(n):
        if cliff_at is not None and rng.random() < cliff_share:
            pos = cliff_at * 600 + rng.uniform(0, 6)
        elif rng.random() < 0.5:
            pos = 600
        else:
            pos = rng.uniform(0, 600)
        events.append(ev(f"u{i}", 1, pos))
    return build(events)


def test_finds_the_cliff():
    ds = listeners(4000, cliff_at=0.42, cliff_share=0.15)
    (h, *rest) = find_hotspots(ds, "s1", 1)
    assert h.start == pytest.approx(0.42, abs=0.011)
    assert h.drop == pytest.approx(0.15, abs=0.03)
    assert h.seconds[0] == pytest.approx(252, abs=7)
    assert all(r.drop < 0.03 for r in rest)


def test_steady_trickle_has_no_hotspots():
    assert find_hotspots(listeners(4000), "s1", 1, min_drop=0.02) == []


def test_outro_is_ignored():
    ds = listeners(4000, cliff_at=0.95, cliff_share=0.3)
    assert all(h.start < 0.9 for h in find_hotspots(ds, "s1", 1))
