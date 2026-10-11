"""Collapse progress pings into views: one per listener per episode."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from .events import Event

Key = tuple[str, str, int]  # (series, user, episode)


@dataclass
class View:
    series: str
    user: str
    episode: int
    reached: float  # furthest position heard, seconds
    first: datetime
    last: datetime


@dataclass
class Dataset:
    views: dict[Key, View]
    durations: dict[tuple[str, int], float]  # (series, episode) -> seconds

    def completion(self, v: View) -> float | None:
        """Share of the episode heard, 0..1, or None if its length is unknown."""
        d = self.durations.get((v.series, v.episode))
        return min(1.0, v.reached / d) if d else None

    def series(self) -> list[str]:
        return sorted({k[0] for k in self.views})

    def episodes(self, series: str) -> list[int]:
        return sorted({k[2] for k in self.views if k[0] == series})


def build(events: Iterable[Event]) -> Dataset:
    """One pass over the events; memory grows with views, not with pings."""
    views: dict[Key, View] = {}
    durations: dict[tuple[str, int], float] = {}
    for e in events:
        key = (e.series, e.user, e.episode)
        v = views.get(key)
        if v is None:
            views[key] = View(e.series, e.user, e.episode, e.position, e.ts, e.ts)
        else:
            v.reached = max(v.reached, e.position)
            v.first = min(v.first, e.ts)
            v.last = max(v.last, e.ts)
        if e.duration:
            k = (e.series, e.episode)
            durations[k] = max(durations.get(k, 0.0), e.duration)
    return Dataset(views, durations)
