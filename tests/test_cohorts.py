from factory import ev

from dropcurve.cohorts import cohorts
from dropcurve.views import build


def test_cohorts_by_first_week():
    week = 7 * 24 * 60
    events = [
        ev("a", 1, 600, 0),
        ev("a", 2, 600, 5),
        ev("b", 1, 600, 10),
        ev("c", 1, 600, week),
        ev("c", 2, 600, week + 1),
        ev("c", 3, 600, week + 2),
    ]
    out = cohorts(build(events), "s1", milestones=(2, 3))
    assert [c.week for c in out] == ["2026-W02", "2026-W03"]
    assert out[0].size == 2 and out[0].reach == {2: 0.5, 3: 0.0}
    assert out[1].reach == {2: 1.0, 3: 1.0}
