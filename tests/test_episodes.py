import pytest
from factory import ev

from dropcurve.episodes import episode_stats
from dropcurve.views import build


def test_completion_per_episode():
    events = [
        ev("u1", 1, 600),
        ev("u2", 1, 560),
        ev("u3", 1, 100),
        ev("u4", 1, 300),
        ev("u1", 2, 590),
        ev("u2", 2, 50),
    ]
    stats = episode_stats(build(events), "s1")
    assert [s.episode for s in stats] == [1, 2]
    e1 = stats[0]
    assert (e1.starters, e1.finishers) == (4, 2)
    assert e1.completion == 0.5
    assert e1.median_heard == pytest.approx((300 + 560) / 2 / 600)
    lo, hi = e1.ci
    assert lo < 0.5 < hi


def test_episodes_without_duration_have_no_starters():
    stats = episode_stats(build([ev("u1", 1, 600, duration=None)]), "s1")
    assert stats[0].starters == 0 and stats[0].completion == 0.0
