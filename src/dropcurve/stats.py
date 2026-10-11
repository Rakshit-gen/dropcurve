"""Small statistics helpers, stdlib only."""

import math


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Behaves at 0, n and small n."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> float:
    """z statistic for p1 - p2 with a pooled standard error. 0 when undefined."""
    if not n1 or not n2:
        return 0.0
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return 0.0 if se == 0 else (x1 / n1 - x2 / n2) / se


def median(values) -> float:
    s = sorted(values)
    if not s:
        return float("nan")
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def quantile(values, q: float) -> float:
    """Linear-interpolation quantile, the same as numpy's default."""
    s = sorted(values)
    if not s:
        return float("nan")
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)
