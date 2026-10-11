"""Kaplan-Meier survival over episodes: the chance a new listener gets past
episode k.

The plain funnel undercounts deep listeners in a fresh dataset, because
people who started last week haven't had time to get far. Survival analysis
handles that: a listener who is still active is "censored", counted while
they were at risk and not counted as lost.
"""

from dataclasses import dataclass

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


def listeners(ds: Dataset, series: str) -> list[Listener]:
    depth: dict[str, int] = {}
    for s, user, ep in ds.views:
        if s == series:
            depth[user] = max(depth.get(user, 0), ep)
    return [Listener(d, True) for d in depth.values()]


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
