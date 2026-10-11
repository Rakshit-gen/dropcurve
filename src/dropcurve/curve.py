"""Within-episode retention: of the people who pressed play, how many are
still listening at each point of the episode."""

from bisect import bisect_left

from .views import Dataset


def heard(ds: Dataset, series: str, episode: int) -> list[float]:
    """Completion (0..1) of every view of one episode with a known length."""
    out = []
    for (s, _, ep), v in ds.views.items():
        if s == series and ep == episode:
            c = ds.completion(v)
            if c is not None:
                out.append(c)
    return out


def retention_curve(ds: Dataset, series: str, episode: int, points: int = 100) -> list[float]:
    """Share of starters who got at least i/points of the way in, for i = 0..points.

    curve[0] is always 1.0 (everyone started); curve[points] is the share who
    reached the very end.
    """
    values = sorted(heard(ds, series, episode))
    n = len(values)
    if not n:
        return []
    # A listener counts at point x if they reached x; tiny float error at the
    # end of the file should not knock finishers out of the last point.
    eps = 1e-9
    return [(n - bisect_left(values, i / points - eps)) / n for i in range(points + 1)]
