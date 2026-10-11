from factory import T0, ev

from dropcurve.views import build


def test_pings_collapse_to_one_view():
    ds = build([ev("u1", 1, 60, 1), ev("u1", 1, 300, 5), ev("u1", 1, 120, 9)])
    (v,) = ds.views.values()
    assert v.reached == 300  # seeking back does not undo what was heard
    assert (v.last - v.first).total_seconds() == 8 * 60
    assert ds.completion(v) == 0.5


def test_completion_caps_at_one_and_needs_a_duration():
    ds = build([ev("u1", 1, 650), ev("u2", 2, 30, duration=None)])
    by_ep = {v.episode: v for v in ds.views.values()}
    assert ds.completion(by_ep[1]) == 1.0
    assert ds.completion(by_ep[2]) is None


def test_series_and_episodes():
    ds = build([ev("u1", 3, 1), ev("u1", 1, 1), ev("u2", 1, 1, series="s2")])
    assert ds.series() == ["s1", "s2"]
    assert ds.episodes("s1") == [1, 3]
    assert ds.views[("s1", "u1", 1)].first == T0


def test_paywall_variant_per_listener():
    from dataclasses import replace

    a = replace(ev("u1", 1, 10), free=8)
    b = replace(ev("u2", 1, 10), free=12)
    c = ev("u3", 1, 10)
    ds = build([a, b, c])
    assert ds.walls == {("s1", "u1"): 8, ("s1", "u2"): 12}
