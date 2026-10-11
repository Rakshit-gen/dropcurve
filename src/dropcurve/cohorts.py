"""Cohorts by the week people found the series.

If listeners who arrived in March get further than those who arrived in
January, something changed: a new cover, a fixed episode, a different ad
campaign bringing different people.
"""

from dataclasses import dataclass
from datetime import datetime

from .views import Dataset


@dataclass
class Cohort:
    week: str  # ISO week, e.g. 2026-W02
    size: int
    reach: dict[int, float]  # episode -> share of the cohort who started it


def week_of(ts: datetime) -> str:
    y, w, _ = ts.isocalendar()
    return f"{y}-W{w:02d}"


def cohorts(ds: Dataset, series: str, milestones=(2, 3, 5, 10)) -> list[Cohort]:
    first: dict[str, datetime] = {}
    depth: dict[str, int] = {}
    for (s, user, ep), v in ds.views.items():
        if s != series:
            continue
        first[user] = min(first.get(user, v.first), v.first)
        depth[user] = max(depth.get(user, 0), ep)
    groups: dict[str, list[str]] = {}
    for user, ts in first.items():
        groups.setdefault(week_of(ts), []).append(user)
    out = []
    for week in sorted(groups):
        users = groups[week]
        reach = {}
        for k in milestones:
            started = sum((series, u, k) in ds.views for u in users)
            reach[k] = started / len(users)
        out.append(Cohort(week, len(users), reach))
    return out
