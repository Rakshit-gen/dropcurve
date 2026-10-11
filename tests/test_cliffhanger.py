from factory import ev

from dropcurve.cliffhanger import endings
from dropcurve.views import build


def test_pull_within_a_day():
    events = [
        ev("a", 1, 600, minutes=10),
        ev("a", 2, 100, minutes=12),  # straight on
        ev("b", 1, 600, minutes=10),
        ev("b", 2, 100, minutes=60 * 30),  # next day+
        ev("c", 1, 600, minutes=10),  # never came back
        ev("d", 1, 200, minutes=10),
        ev("d", 2, 100, minutes=11),  # did not finish ep1
    ]
    (e1,) = endings(build(events), "s1")
    assert (e1.finishers, e1.pulled) == (3, 1)
    assert round(e1.pull, 3) == 0.333


def test_last_episode_has_no_ending_to_score():
    assert endings(build([ev("a", 1, 600)]), "s1") == []
