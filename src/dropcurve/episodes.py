"""Per-episode completion: how many who start an episode finish it."""

from dataclasses import dataclass

from .stats import median, wilson
from .views import Dataset

BOUNCE_SECONDS = 30.0  # left before the hook had a chance
FINISH = 0.9  # heard 90% or more: the credits and next-episode teaser can be skipped


@dataclass
class EpisodeStats:
    episode: int
    starters: int
    finishers: int
    median_heard: float | None  # median share of the episode heard, 0..1
    duration: float | None
    bounced: int = 0  # starters who left within the first BOUNCE_SECONDS

    @property
    def bounce_rate(self) -> float:
        return self.bounced / self.starters if self.starters else 0.0

    @property
    def completion(self) -> float:
        return self.finishers / self.starters if self.starters else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.finishers, self.starters)


def episode_stats(
    ds: Dataset, series: str, finish: float = FINISH, bounce_seconds: float = BOUNCE_SECONDS
) -> list[EpisodeStats]:
    by_ep: dict[int, list[float]] = {}
    bounced: dict[int, int] = {}
    for (s, _, ep), v in ds.views.items():
        if s != series:
            continue
        c = ds.completion(v)
        by_ep.setdefault(ep, [])
        if c is not None:
            by_ep[ep].append(c)
            bounced[ep] = bounced.get(ep, 0) + (v.reached < bounce_seconds)
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
                bounced=bounced.get(ep, 0),
            )
        )
    return out
