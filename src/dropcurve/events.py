"""Listening events: one row per progress ping from the player."""

import csv
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

# Accepted column names, so most player exports load without renaming.
ALIASES = {
    "user": ("user", "user_id", "uid"),
    "series": ("series", "series_id", "show", "show_id"),
    "episode": ("episode", "episode_number", "ep"),
    "position": ("position", "position_s", "pos"),
    "duration": ("duration", "duration_s", "length"),
    "ts": ("ts", "timestamp", "time"),
    "kind": ("kind", "event", "type"),
    "coins": ("coins", "amount", "price"),
    "free": ("free_episodes", "free", "wall"),
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
    kind: str = "play"  # "play" for progress pings, "unlock" for a paid unlock
    coins: float = 0.0  # what an unlock cost
    free: int | None = None  # free episodes this listener gets (their A/B variant)


class EventError(ValueError):
    pass


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
        raise EventError(f"missing columns: {', '.join(missing)} (have: {', '.join(header)})")
    return cols


def parse_ts(value) -> datetime:
    """ISO 8601 (with or without Z), or Unix time in seconds or milliseconds.

    Times without a zone are taken as UTC, so every timestamp compares cleanly.
    """
    if isinstance(value, int | float) or str(value).replace(".", "", 1).isdigit():
        n = float(value)
        if n > 1e11:  # milliseconds
            n /= 1000
        return datetime.fromtimestamp(n, UTC)
    ts = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def parse_row(row: dict, cols: dict[str, str]) -> Event:
    dur = row.get(cols.get("duration", ""), "")
    e = Event(
        user=str(row[cols["user"]]),
        series=str(row[cols["series"]]),
        episode=int(row[cols["episode"]]),
        position=float(row[cols["position"]]),
        duration=float(dur) if dur not in ("", None) else None,
        ts=parse_ts(row[cols["ts"]]),
        kind=(str(row.get(cols.get("kind", ""), "")) or "play").strip().lower(),
        coins=float(row.get(cols.get("coins", ""), "") or 0),
        free=int(row.get(cols.get("free", ""), "") or 0) or None,
    )
    if e.kind not in ("play", "unlock"):
        raise ValueError(f"unknown event kind {e.kind!r} (expected play or unlock)")
    if not e.user or not e.series:
        raise ValueError("empty user or series")
    if e.episode < 1:
        raise ValueError(f"episode {e.episode}: episodes are numbered from 1")
    if e.position < 0 or (e.duration is not None and e.duration <= 0):
        raise ValueError("negative position or non-positive duration")
    return e


def _rows(path) -> Iterator[tuple[int, dict]]:
    """(line number, raw row) pairs from a CSV or JSONL file."""
    suffix = str(path).lower().rsplit(".", 1)[-1]
    with open(path, newline="") as f:
        if suffix in ("jsonl", "ndjson"):
            for n, line in enumerate(f, 1):
                if line.strip():
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as e:
                        obj = {"__error__": str(e)}
                    yield n, {k: ("" if v is None else v) for k, v in obj.items()}
        else:
            reader = csv.DictReader(f)
            for row in reader:
                yield reader.line_num, row


def read_events(path, errors: list[str] | None = None) -> Iterator[Event]:
    """Read a .csv, .jsonl or .ndjson file of events.

    Bad rows raise EventError naming the line, unless an `errors` list is
    given; then they are recorded there and skipped.
    """
    cols = None
    for line, row in _rows(path):
        if cols is None and "__error__" not in row:
            cols = resolve_columns(list(row))
        try:
            if "__error__" in row:
                raise ValueError(row["__error__"])
            yield parse_row(row, cols)
        except (ValueError, KeyError, TypeError) as e:
            msg = f"{path}:{line}: {e}"
            if errors is None:
                raise EventError(msg) from e
            errors.append(msg)


COLUMNS = ("user", "series", "episode", "position", "duration", "ts", "kind", "coins", "free")


def write_events(events, path) -> int:
    """Write events as CSV (or JSONL if the name ends in .jsonl). Returns the count."""
    jsonl = str(path).lower().endswith((".jsonl", ".ndjson"))
    n = 0
    with open(path, "w", newline="") as f:
        writer = None if jsonl else csv.writer(f)
        if writer:
            writer.writerow(COLUMNS)
        for e in events:
            row = [
                e.user,
                e.series,
                e.episode,
                e.position,
                "" if e.duration is None else e.duration,
                e.ts.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                e.kind,
                e.coins or "",
                e.free or "",
            ]
            if writer:
                writer.writerow(row)
            else:
                f.write(json.dumps(dict(zip(COLUMNS, row, strict=True))) + "\n")
            n += 1
    return n
