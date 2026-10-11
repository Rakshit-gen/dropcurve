"""The season funnel: how far into a series people get."""

from dataclasses import dataclass

from .episodes import FINISH
from .stats import wilson
from .views import Dataset


@dataclass
class Step:
    episode: int
    listeners: int  # people who started this episode
    reach: float  # listeners / people who started episode 1
    finished: int = 0  # listeners who finished it
    continued: int = 0  # finishers who then started the next episode
    last: bool = False  # no next episode yet, so no continuation to measure

    @property
    def continuation(self) -> float | None:
        """Of those who finished this episode, the share who started the next."""
        if self.last or not self.finished:
            return None
        return self.continued / self.finished

    @property
    def continuation_ci(self) -> tuple[float, float]:
        return wilson(self.continued, self.finished)


def listeners_by_episode(ds: Dataset, series: str) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    for s, user, ep in ds.views:
        if s == series:
            out.setdefault(ep, set()).add(user)
    return out


def funnel(ds: Dataset, series: str, finish: float = FINISH) -> list[Step]:
    by_ep = listeners_by_episode(ds, series)
    if not by_ep:
        return []
    first = len(by_ep.get(1, ())) or len(by_ep[min(by_ep)])
    last = max(by_ep)
    steps = []
    for ep in range(1, last + 1):
        users = by_ep.get(ep, set())
        finishers = {u for u in users if (ds.completion(ds.views[(series, u, ep)]) or 0) >= finish}
        nxt = by_ep.get(ep + 1, set())
        steps.append(
            Step(
                episode=ep,
                listeners=len(users),
                reach=len(users) / first if first else 0.0,
                finished=len(finishers),
                continued=len(finishers & nxt) if ep < last else 0,
                last=ep == last,
            )
        )
    return steps
