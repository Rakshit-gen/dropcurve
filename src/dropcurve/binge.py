"""Listening sessions: how many episodes people play in one sitting."""

from dataclasses import dataclass
from datetime import timedelta

from .stats import median, quantile
from .views import Dataset

SESSION_GAP = timedelta(minutes=30)


@dataclass
class BingeStats:
    sessions: int
    median_episodes: float
    p90_episodes: float
    binge_share: float  # sessions with 3 or more episodes


def sessions(ds: Dataset, series: str, gap: timedelta = SESSION_GAP) -> list[int]:
    """Episodes per session, for every session in the series."""
    by_user: dict[str, list] = {}
    for (s, user, _), v in ds.views.items():
        if s == series:
            by_user.setdefault(user, []).append(v)
    counts = []
    for views in by_user.values():
        views.sort(key=lambda v: v.first)
        n, end = 1, views[0].last
        for v in views[1:]:
            if v.first - end > gap:
                counts.append(n)
                n = 0
            n += 1
            end = max(end, v.last)
        counts.append(n)
    return counts


def binge_stats(ds: Dataset, series: str, gap: timedelta = SESSION_GAP) -> BingeStats | None:
    counts = sessions(ds, series, gap)
    if not counts:
        return None
    return BingeStats(
        sessions=len(counts),
        median_episodes=median(counts),
        p90_episodes=quantile(counts, 0.9),
        binge_share=sum(c >= 3 for c in counts) / len(counts),
    )
