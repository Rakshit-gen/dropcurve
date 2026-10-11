import pytest

from dropcurve.survival import Listener, kaplan_meier


def test_without_censoring_it_is_the_funnel():
    people = [Listener(d, True) for d in [1, 1, 2, 3, 3, 3, 4, 5, 5, 5]]
    km = kaplan_meier(people)
    # Share who went past episode k: 8/10, 7/10, 4/10, 3/10, 0.
    assert [round(p.survival, 3) for p in km] == [0.8, 0.7, 0.4, 0.3, 0.0]
    assert km[0].at_risk == 10 and km[0].lost == 2


def test_censored_listeners_are_not_counted_as_lost():
    people = [Listener(1, True), Listener(1, False), Listener(2, True), Listener(3, True)]
    km = kaplan_meier(people)
    assert km[0].survival == pytest.approx(0.75)
    # At ep 2: 2 at risk (the censored one left the risk set), 1 lost.
    assert km[1].at_risk == 2
    assert km[1].survival == pytest.approx(0.75 * 0.5)


def test_recent_and_caught_up_listeners_are_censored():
    from factory import ev

    from dropcurve.survival import listeners
    from dropcurve.views import build

    day = 24 * 60
    events = [
        ev("old", 1, 600, minutes=0),  # stopped at ep1 30 days ago: lost
        ev("new", 1, 600, minutes=29 * day),  # started yesterday: censored
        ev("fan", 1, 600, minutes=0),
        ev("fan", 2, 600, minutes=1),
        ev("fan", 3, 600, minutes=2),  # finished everything there is: censored
        ev("x", 3, 10, minutes=30 * day),  # newest event in the data
    ]
    people = {p.depth: p for p in listeners(build(events), "s1")}
    got = sorted((p.depth, p.churned) for p in listeners(build(events), "s1"))
    assert got == [(1, False), (1, True), (3, False), (3, False)]
    assert people
