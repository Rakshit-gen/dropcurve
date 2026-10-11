"""How hard each episode's ending pulls people into the next one.

A finisher who starts the next episode within a day was hooked by the
ending. Comparing that rate across a season shows which endings work and
which ones let people put the phone down.
"""

from dataclasses import dataclass
from datetime import timedelta

from .episodes import FINISH
from .stats import wilson
from .views import Dataset


@dataclass
class Ending:
    episode: int
    finishers: int
    pulled: int  # finishers who started the next episode within the window
    z: float = 0.0  # against the rest of the season; negative = weaker ending
    verdict: str = ""  # "weak", "strong" or ""

    @property
    def pull(self) -> float:
        return self.pulled / self.finishers if self.finishers else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.pulled, self.finishers)


def endings(
    ds: Dataset, series: str, window: timedelta = timedelta(hours=24), finish: float = FINISH
) -> list[Ending]:
    eps = sorted({ep for s, _, ep in ds.views if s == series})
    out = []
    for ep in eps:
        if ep + 1 not in eps:
            continue
        finishers = pulled = 0
        for (s, user, e), v in ds.views.items():
            if s != series or e != ep or (ds.completion(v) or 0) < finish:
                continue
            finishers += 1
            nxt = ds.views.get((series, user, ep + 1))
            if nxt and timedelta(0) <= nxt.first - v.last <= window:
                pulled += 1
            elif nxt and nxt.first < v.last and nxt.first >= v.first:
                pulled += 1  # started the next one before the last ping of this one
        out.append(Ending(ep, finishers, pulled))
    return out
