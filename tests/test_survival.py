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
