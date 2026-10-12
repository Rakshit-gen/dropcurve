from dataclasses import replace

from dropcurve.episodes import episode_stats
from dropcurve.funnel import funnel
from dropcurve.synth import Truth, generate
from dropcurve.views import build


def test_generator_is_deterministic():
    assert generate(50, seed=3) == generate(50, seed=3)
    assert generate(50, seed=3) != generate(50, seed=4)


def test_baseline_rates_come_out():
    t = Truth(episodes=6)
    ds = build(generate(3000, t))
    stats = episode_stats(ds, t.series)
    # Finish = not leaving inside the episode (0.9), plus leavers who passed 90%.
    for s in stats:
        assert 0.88 < s.completion < 0.93
    steps = funnel(ds, t.series)
    assert 0.89 < steps[0].continuation < 0.95


def test_paywall_variants_unlock_after_the_free_episodes():
    events = generate(300, replace(Truth(), walls=(3, 6)), seed=2)
    assert {e.free for e in events} == {3, 6}
    unlocks = [e for e in events if e.kind == "unlock"]
    assert unlocks
    assert all(e.episode > e.free and e.coins == 15.0 for e in unlocks)
    # Nobody plays past the wall without paying for that episode.
    paid = {(e.user, e.episode) for e in unlocks}
    for e in events:
        if e.kind == "play" and e.episode > e.free:
            assert (e.user, e.episode) in paid
