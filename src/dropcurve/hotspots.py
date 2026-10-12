"""Drop-off hotspots: the moments in an episode where listeners leave
noticeably faster than they do everywhere else in it.

A steady trickle of people leaving is normal. A cliff at 4:10 usually means
something happened at 4:10: an ad break, a long recap, a scene that drags,
a jarring music cue, a bad edit.
"""

from dataclasses import dataclass

from .curve import heard, retention_curve
from .stats import median
from .views import Dataset


@dataclass
class Hotspot:
    start: float  # share of the episode, 0..1
    end: float
    drop: float  # share of starters lost in this stretch
    excess: float  # how many times the episode's typical loss rate
    seconds: tuple[float, float] | None  # (start, end) in seconds, if the length is known


def find_hotspots(
    ds: Dataset,
    series: str,
    episode: int,
    points: int = 100,
    factor: float = 3.0,
    min_drop: float = 0.01,
    skip_intro: float = 0.02,
    skip_outro: float = 0.1,
    min_people: int = 10,
) -> list[Hotspot]:
    """Stretches where the loss per step is more than `factor` times the median.

    The first `skip_intro` and last `skip_outro` of the episode are left out:
    people bounce in the first seconds and skip the credits everywhere, and
    neither tells you anything about the story.

    A stretch must also lose at least `min_people` listeners. Deep episodes
    have few listeners, and there every single person leaving looks like a
    spike against a typical loss of nearly zero.
    """
    curve = retention_curve(ds, series, episode, points)
    if not curve:
        return []
    n = len(heard(ds, series, episode))
    drops = [curve[i - 1] - curve[i] for i in range(1, points + 1)]
    lo = int(skip_intro * points)
    hi = points - int(skip_outro * points)
    body = drops[lo:hi]
    if not body:
        return []
    # At least half a listener per step, so a sparse episode can't divide by ~0.
    typical = max(median(body), 0.5 / n)
    hot = [lo <= i < hi and d > factor * typical and d >= min_drop / 2 for i, d in enumerate(drops)]

    out = []
    i = 0
    duration = ds.durations.get((series, episode))
    while i < points:
        if not hot[i]:
            i += 1
            continue
        j = i
        while j + 1 < points and hot[j + 1]:
            j += 1
        drop = sum(drops[i : j + 1])
        if drop >= min_drop and round(drop * n) >= min_people:
            start, end = i / points, (j + 1) / points
            secs = (start * duration, end * duration) if duration else None
            out.append(Hotspot(start, end, drop, drop / ((j - i + 1) * typical), secs))
        i = j + 1
    return sorted(out, key=lambda h: -h.drop)
