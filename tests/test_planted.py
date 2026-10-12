"""The analysis must find every problem planted in the demo data."""

import pytest

from dropcurve.synth import Truth, generate
from dropcurve.views import build

T = Truth.demo()


@pytest.fixture(scope="module")
def ds():
    return build(generate(6000, T, seed=11))


def test_finds_the_ad_break_cliff(ds):
    from dropcurve.hotspots import find_hotspots

    hot = find_hotspots(ds, T.series, 6)
    assert hot, "no hotspot found in episode 6"
    assert hot[0].start == pytest.approx(0.41, abs=0.011)
    for ep in (3, 4, 5, 7):
        assert find_hotspots(ds, T.series, ep, min_drop=0.03) == []


def test_finds_the_weak_ending(ds):
    from dropcurve.cliffhanger import endings, score_endings

    ends = endings(ds, T.series)
    score_endings(ends)
    assert [e.episode for e in ends if e.verdict == "weak"] == [9]
    assert not [e for e in ends if e.verdict == "strong"]


def test_finds_the_slow_episode(ds):
    from dropcurve.anomalies import anomalies
    from dropcurve.episodes import episode_stats

    found = anomalies(episode_stats(ds, T.series))
    # Episode 6 is flagged too, and rightly: the people lost at its ad break
    # never finish it. Episode 14 is the one with no cliff, just a slow drain.
    assert [a.episode for a in found] == [6, 14]
