"""Episodes that finish far worse than the episodes around them.

Completion drifts down over a season as casual listeners leave, so each
episode is compared with the line between its two neighbours, not with the
season average. The noise scale is the typical size of those residuals
across the whole season (a robust MAD), so one bad episode can't hide itself.
"""

from dataclasses import dataclass

from .episodes import EpisodeStats
from .stats import median


@dataclass
class Anomaly:
    episode: int
    completion: float
    expected: float  # what the neighbours predict
    score: float  # residual in robust standard deviations; negative = worse


def anomalies(
    stats: list[EpisodeStats], cut: float = 3.5, min_starters: int = 50, floor: float = 0.01
) -> list[Anomaly]:
    usable = [s for s in stats if s.starters >= min_starters]
    if len(usable) < 3:
        return []
    r = [s.completion for s in usable]
    expected = []
    for i in range(len(r)):
        near = [r[j] for j in (i - 1, i + 1) if 0 <= j < len(r)]
        expected.append(sum(near) / len(near))
    resid = [a - b for a, b in zip(r, expected, strict=True)]
    scale = 1.4826 * max(median([abs(x) for x in resid]), floor)
    return [
        Anomaly(s.episode, s.completion, e, x / scale)
        for s, e, x in zip(usable, expected, resid, strict=True)
        if x / scale <= -cut
    ]
