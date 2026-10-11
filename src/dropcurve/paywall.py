"""Where should the paywall go?

Pay-per-episode apps give the first N episodes free and charge coins after
that. A wall too early loses people who weren't hooked yet; too late gives
away the episodes that hook them. The honest way to choose N is to test
several values, so this module reads A/B variants (each listener's free
episode count) and measures what each one earned per new listener.
"""

import math
from dataclasses import dataclass

from .episodes import FINISH
from .stats import wilson
from .views import Dataset


@dataclass
class WallResult:
    free: int  # free episodes in this variant
    starters: int  # listeners who started episode 1
    reached: int  # finished the last free episode, so they met the wall
    payers: int  # unlocked at least one episode
    coins: float  # total coins spent
    sum_sq: float  # sum of squared coins per listener, for the standard error

    @property
    def per_starter(self) -> float:
        return self.coins / self.starters if self.starters else 0.0

    @property
    def se(self) -> float:
        """Standard error of coins per starter."""
        n = self.starters
        if n < 2:
            return math.inf
        mean = self.per_starter
        var = (self.sum_sq - n * mean * mean) / (n - 1)
        return math.sqrt(max(var, 0.0) / n)

    @property
    def conversion(self) -> float:
        """Of those who met the wall, the share who paid."""
        return self.payers / self.reached if self.reached else 0.0

    @property
    def conversion_ci(self) -> tuple[float, float]:
        return wilson(self.payers, self.reached)


def wall_results(
    ds: Dataset, series: str, default_free: int | None = None, finish: float = FINISH
) -> list[WallResult]:
    starters: dict[str, int] = {}
    for s, user, ep in ds.views:
        if s == series and ep == 1:
            free = ds.walls.get((series, user), default_free)
            if free:
                starters[user] = free
    spent: dict[str, float] = {}
    for (s, user, _), coins in ds.unlocks.items():
        if s == series and user in starters:
            spent[user] = spent.get(user, 0.0) + coins

    groups: dict[int, WallResult] = {}
    for user, free in starters.items():
        g = groups.setdefault(free, WallResult(free, 0, 0, 0, 0.0, 0.0))
        g.starters += 1
        last_free = ds.views.get((series, user, free))
        if (last_free and (ds.completion(last_free) or 0) >= finish) or user in spent:
            g.reached += 1
        c = spent.get(user, 0.0)
        if c > 0:
            g.payers += 1
        g.coins += c
        g.sum_sq += c * c
    return [groups[k] for k in sorted(groups)]


@dataclass
class Verdict:
    best: WallResult
    runner_up: WallResult | None
    z: float  # best minus runner-up, in standard errors
    confident: bool  # z clears the cut: the winner is not just noise

    def describe(self) -> str:
        b = self.best
        text = f"{b.free} free episodes earns {b.per_starter:.2f} coins per new listener"
        if self.runner_up is None:
            return text + " (only one variant in the data)"
        r = self.runner_up
        text += f", against {r.per_starter:.2f} with {r.free} free (z = {self.z:.1f})"
        if not self.confident:
            text += "; not enough data to call it yet"
        return text


def compare(results: list[WallResult], z_cut: float = 1.96) -> Verdict | None:
    """Pick the variant with the most coins per starter, and say whether the
    lead over the second best is bigger than the noise."""
    ranked = sorted((r for r in results if r.starters), key=lambda r: -r.per_starter)
    if not ranked:
        return None
    best = ranked[0]
    if len(ranked) == 1:
        return Verdict(best, None, 0.0, False)
    second = ranked[1]
    se = math.hypot(best.se, second.se)
    z = (best.per_starter - second.per_starter) / se if se and math.isfinite(se) else 0.0
    return Verdict(best, second, z, z >= z_cut)
