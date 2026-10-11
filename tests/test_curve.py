import pytest
from factory import ev

from dropcurve.curve import retention_curve
from dropcurve.views import build


def test_curve_shape():
    # 4 listeners: leave at 25%, 50%, 75%, finish.
    ds = build([ev(f"u{i}", 1, p) for i, p in enumerate([150, 300, 450, 600])])
    c = retention_curve(ds, "s1", 1, points=4)
    assert c == [1.0, 1.0, 0.75, 0.5, 0.25]


def test_curve_is_monotonic():
    import random

    rng = random.Random(1)
    ds = build([ev(f"u{i}", 1, rng.uniform(0, 600)) for i in range(500)])
    c = retention_curve(ds, "s1", 1)
    assert len(c) == 101 and c[0] == 1.0
    assert all(a >= b for a, b in zip(c, c[1:], strict=False))
    assert c[50] == pytest.approx(0.5, abs=0.07)


def test_unknown_episode():
    assert retention_curve(build([ev("u1", 1, 10)]), "s1", 9) == []
