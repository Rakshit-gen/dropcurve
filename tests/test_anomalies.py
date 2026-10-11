from dropcurve.anomalies import anomalies
from dropcurve.episodes import EpisodeStats


def ep(n, rate, starters=1000):
    return EpisodeStats(n, starters, int(rate * starters), None, 600.0)


def test_dip_against_neighbours_not_the_season():
    # Completion slides from 80% to 60% over the season; ep 7 dips to 52%.
    rates = [0.80, 0.79, 0.77, 0.75, 0.73, 0.71, 0.52, 0.68, 0.66, 0.64, 0.62, 0.60]
    found = anomalies([ep(i + 1, r) for i, r in enumerate(rates)])
    assert [a.episode for a in found] == [7]
    assert abs(found[0].expected - 0.695) < 1e-9
    assert found[0].score < -10


def test_small_episodes_are_skipped():
    rates = [0.8, 0.8, 0.8, 0.1, 0.8, 0.8]
    stats = [ep(i + 1, r) for i, r in enumerate(rates)]
    stats[3] = ep(4, 0.1, starters=10)
    assert anomalies(stats) == []
