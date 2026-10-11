"""Per-episode completion: how many who start an episode finish it."""

from dataclasses import dataclass

from .stats import median, wilson
from .views import Dataset

FINISH = 0.9  # heard 90% or more: the credits and next-episode teaser can be skipped


@dataclass
class EpisodeStats:
    episode: int
    starters: int
    finishers: int
    median_heard: float | None  # median share of the episode heard, 0..1
    duration: float | None

    @property
    def completion(self) -> float:
        return self.finishers / self.starters if self.starters else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.finishers, self.starters)


def episode_stats(ds: Dataset, series: str, finish: float = FINISH) -> list[EpisodeStats]:
    by_ep: dict[int, list[float]] = {}
    for (s, _, ep), v in ds.views.items():
        if s != series:
            continue
        c = ds.completion(v)
        by_ep.setdefault(ep, [])
        if c is not None:
            by_ep[ep].append(c)
    out = []
    for ep in sorted(by_ep):
        heard = by_ep[ep]
        out.append(
            EpisodeStats(
                episode=ep,
                starters=len(heard),
                finishers=sum(c >= finish for c in heard),
                median_heard=median(heard) if heard else None,
                duration=ds.durations.get((series, ep)),
            )
        )
    return out
