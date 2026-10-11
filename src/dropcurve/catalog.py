"""Episode lengths from a catalog file, for players that don't send duration."""

import csv

from .events import EventError


def load_catalog(path) -> dict[tuple[str, int], float]:
    """Read series,episode,duration rows (duration in seconds)."""
    out = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        need = {"series", "episode", "duration"}
        if not need <= set(reader.fieldnames or []):
            raise EventError(f"{path}: catalog needs columns series, episode, duration")
        for row in reader:
            try:
                out[(row["series"], int(row["episode"]))] = float(row["duration"])
            except ValueError as e:
                raise EventError(f"{path}:{reader.line_num}: {e}") from e
    return out


def apply_catalog(ds, catalog: dict[tuple[str, int], float]) -> None:
    """The catalog wins over durations seen in events: it is the source of truth."""
    ds.durations.update(catalog)
