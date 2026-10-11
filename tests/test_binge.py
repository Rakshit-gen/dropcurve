from factory import ev

from dropcurve.binge import binge_stats, sessions
from dropcurve.views import build


def test_sessions_split_on_gaps():
    events = [
        # u1: eps 1-3 back to back, then ep 4 the next day
        ev("u1", 1, 600, 0),
        ev("u1", 1, 600, 10),
        ev("u1", 2, 600, 15),
        ev("u1", 3, 600, 30),
        ev("u1", 4, 600, 60 * 24),
        ev("u2", 1, 100, 0),
    ]
    assert sorted(sessions(build(events), "s1")) == [1, 1, 3]
    b = binge_stats(build(events), "s1")
    assert b.sessions == 3 and b.median_episodes == 1
    assert round(b.binge_share, 3) == 0.333


def test_no_data():
    assert binge_stats(build([]), "s1") is None
