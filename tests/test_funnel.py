from factory import ev

from dropcurve.funnel import funnel
from dropcurve.views import build


def test_reach_and_continuation():
    events = []
    # 10 people start ep1; 8 finish; 6 of those start ep2; 3 reach ep3.
    for i in range(10):
        events.append(ev(f"u{i}", 1, 600 if i < 8 else 100))
    for i in range(6):
        events.append(ev(f"u{i}", 2, 600 if i < 4 else 50))
    for i in range(3):
        events.append(ev(f"u{i}", 3, 600))
    steps = funnel(build(events), "s1")
    assert [s.listeners for s in steps] == [10, 6, 3]
    assert [round(s.reach, 2) for s in steps] == [1.0, 0.6, 0.3]
    assert steps[0].continuation == 6 / 8
    assert steps[1].continuation == 3 / 4
    assert steps[2].continuation is None  # nothing after the last episode


def test_missing_episode_in_the_middle():
    steps = funnel(build([ev("u1", 1, 600), ev("u1", 3, 600)]), "s1")
    assert [s.listeners for s in steps] == [1, 0, 1]
    assert steps[0].continuation == 0.0
