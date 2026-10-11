"""Listening events: one row per progress ping from the player."""

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

# Accepted column names, so most player exports load without renaming.
ALIASES = {
    "user": ("user", "user_id", "uid"),
    "series": ("series", "series_id", "show", "show_id"),
    "episode": ("episode", "episode_number", "ep"),
    "position": ("position", "position_s", "pos"),
    "duration": ("duration", "duration_s", "length"),
    "ts": ("ts", "timestamp", "time"),
}
REQUIRED = ("user", "series", "episode", "position", "ts")


@dataclass(frozen=True)
class Event:
    user: str
    series: str
    episode: int
    position: float  # seconds into the episode
    duration: float | None  # episode length in seconds, if the player sent it
    ts: datetime


def resolve_columns(header: list[str]) -> dict[str, str]:
    """Map our field names to the file's column names."""
    lower = {h.strip().lower(): h for h in header}
    cols = {}
    for field, names in ALIASES.items():
        for name in names:
            if name in lower:
                cols[field] = lower[name]
                break
    missing = [f for f in REQUIRED if f not in cols]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)} (have: {', '.join(header)})")
    return cols


def parse_row(row: dict, cols: dict[str, str]) -> Event:
    dur = row.get(cols.get("duration", ""), "")
    return Event(
        user=row[cols["user"]],
        series=row[cols["series"]],
        episode=int(row[cols["episode"]]),
        position=float(row[cols["position"]]),
        duration=float(dur) if dur not in ("", None) else None,
        ts=datetime.fromisoformat(row[cols["ts"]]),
    )


def read_csv(path) -> Iterator[Event]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        cols = resolve_columns(reader.fieldnames or [])
        for row in reader:
            yield parse_row(row, cols)
