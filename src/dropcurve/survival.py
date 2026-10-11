"""Kaplan-Meier survival over episodes: the chance a new listener gets past
episode k.

The plain funnel undercounts deep listeners in a fresh dataset, because
people who started last week haven't had time to get far. Survival analysis
handles that: a listener who is still active is "censored", counted while
they were at risk and not counted as lost.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .views import Dataset


@dataclass
class Listener:
    depth: int  # furthest episode started
    churned: bool  # False = censored (may still go on)


@dataclass
class SurvivalPoint:
    episode: int
    at_risk: int
    lost: int
    survival: float  # P(goes past this episode)


def listeners(
    ds: Dataset, series: str, active_days: float = 7.0, now: datetime | None = None
) -> list[Listener]:
    """One Listener per person, censored when we can't yet call them lost:

    - they were active in the last `active_days` before `now` (default: the
      newest event in the data), or
    - they have caught up with the newest episode, so there was nothing left
      to listen to.
    """
    depth: dict[str, int] = {}
    seen: dict[str, datetime] = {}
    newest_ep = 0
    for (s, user, ep), v in ds.views.items():
        if s != series:
            continue
        depth[user] = max(depth.get(user, 0), ep)
        seen[user] = max(seen.get(user, v.last), v.last)
        newest_ep = max(newest_ep, ep)
    if not depth:
        return []
    now = now or max(seen.values())
    cutoff = now - timedelta(days=active_days)
    return [
        Listener(d, churned=not (seen[u] >= cutoff or d >= newest_ep)) for u, d in depth.items()
    ]


def kaplan_meier(people: list[Listener]) -> list[SurvivalPoint]:
    if not people:
        return []
    last = max(p.depth for p in people)
    out, s = [], 1.0
    for k in range(1, last + 1):
        at_risk = sum(p.depth >= k for p in people)
        lost = sum(p.depth == k and p.churned for p in people)
        if at_risk:
            s *= 1 - lost / at_risk
        out.append(SurvivalPoint(k, at_risk, lost, s))
    return out
