from dataclasses import replace

import pytest
from factory import ev

from dropcurve.paywall import wall_results
from dropcurve.views import build


def listener(user, free, depth, paid_eps=(), coins=10):
    events = [replace(ev(user, ep, 600, minutes=ep), free=free) for ep in range(1, depth + 1)]
    events += [
        replace(ev(user, ep, 0, minutes=ep), kind="unlock", coins=coins, free=free)
        for ep in paid_eps
    ]
    return events


def test_results_per_variant():
    events = []
    events += listener("a", 3, 3, paid_eps=(4, 5))  # met the wall, paid twice
    events += listener("b", 3, 3)  # met the wall, left
    events += listener("c", 3, 1)  # left before the wall
    events += listener("d", 5, 5, paid_eps=(6,))
    events += listener("e", 5, 2)
    res = {r.free: r for r in wall_results(build(events), "s1")}
    three = res[3]
    assert (three.starters, three.reached, three.payers, three.coins) == (3, 2, 1, 20.0)
    assert three.per_starter == pytest.approx(20 / 3)
    assert three.conversion == 0.5
    assert res[5].per_starter == 5.0


def test_default_wall_when_there_is_no_variant_column():
    events = [ev("a", 1, 600), ev("a", 2, 600), replace(ev("a", 3, 0), kind="unlock", coins=7)]
    (r,) = wall_results(build(events), "s1", default_free=2)
    assert (r.free, r.reached, r.payers, r.coins) == (2, 1, 1, 7.0)


def test_standard_error():
    events = []
    for i in range(10):
        events += listener(f"u{i}", 3, 3, paid_eps=(4,) if i < 5 else (), coins=10)
    (r,) = wall_results(build(events), "s1")
    # Coins per listener are 10 x5 and 0 x5: sd = 5.27, se = 1.667.
    assert r.se == pytest.approx(1.6667, abs=1e-3)


def test_compare_calls_a_clear_winner():
    from dropcurve.paywall import WallResult, compare

    def group(free, n, payers, coins_each):
        c = payers * coins_each
        return WallResult(free, n, n // 2, payers, c, payers * coins_each**2)

    v = compare([group(5, 2000, 300, 40), group(8, 2000, 220, 40), group(12, 2000, 120, 40)])
    assert v.best.free == 5 and v.runner_up.free == 8
    assert v.confident and v.z > 3
    assert "5 free episodes earns 6.00 coins per new listener" in v.describe()


def test_compare_with_too_little_data():
    from dropcurve.paywall import WallResult, compare

    v = compare([WallResult(5, 40, 20, 6, 240.0, 9600.0), WallResult(8, 40, 20, 5, 200.0, 8000.0)])
    assert not v.confident
    assert "not enough data" in v.describe()
    assert compare([]) is None
