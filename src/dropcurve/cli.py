"""Command line entry point."""

import argparse
import sys
from dataclasses import replace

from . import __version__
from .curve import retention_curve
from .events import EventError, read_events, write_events
from .funnel import funnel
from .survival import kaplan_meier, listeners, median_depth
from .synth import Truth, generate
from .views import Dataset, build


class UsageError(Exception):
    pass


def _ints(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in text.split(",") if x.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected numbers like 5,8,12, got {text!r}") from None


def load(args) -> tuple[Dataset, str]:
    """Read the events file and pick the series to analyse."""
    ds = build(read_events(args.events))
    names = ds.series()
    if not names:
        raise UsageError(f"{args.events}: no listening events")
    if args.series:
        if args.series not in names:
            raise UsageError(f"no series {args.series!r} (have: {', '.join(names)})")
        return ds, args.series
    if len(names) > 1:
        raise UsageError(f"{len(names)} series in the file, pick one with --series")
    return ds, names[0]


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def cmd_summary(args) -> int:
    ds, series = load(args)
    steps = funnel(ds, series)
    km = kaplan_meier(listeners(ds, series))
    depth = median_depth(km)
    print(f"{series}: {steps[0].listeners} listeners, {len(steps)} episodes")
    print(f"  finished episode 1      {pct(steps[0].finished / steps[0].listeners)}")
    print(f"  started the last one    {pct(steps[-1].reach)}")
    if depth is None:
        print("  median depth            more than half are still going")
    else:
        print(f"  median depth            half don't get past episode {depth}")
    return 0


BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], width: int = 50) -> str:
    """Values in 0..1 as a row of block characters."""
    if not values:
        return ""
    step = (len(values) - 1) / max(width - 1, 1)
    picks = [values[round(i * step)] for i in range(min(width, len(values)))]
    return "".join(BLOCKS[min(7, int(v * 8))] for v in picks)


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def cmd_curve(args) -> int:
    ds, series = load(args)
    curve = retention_curve(ds, series, args.episode)
    if not curve:
        raise UsageError(f"no listens with a known length for episode {args.episode}")
    duration = ds.durations.get((series, args.episode))
    print(f"{series} episode {args.episode}: share of starters still listening")
    print(f"  {sparkline(curve)}")
    for i in range(0, 101, 10):
        at = f"  ({mmss(duration * i / 100)})" if duration else ""
        print(f"  {i:3d}%{at}  {pct(curve[i])}")
    return 0


def cmd_synth(args) -> int:
    truth = Truth.demo()
    if args.walls:
        truth = replace(truth, walls=args.walls)
    n = write_events(generate(args.users, truth, seed=args.seed), args.out)
    print(f"wrote {n} events from {args.users} listeners to {args.out}")
    return 0


def data_args(s: argparse.ArgumentParser) -> None:
    s.add_argument("events", help="event log, .csv or .jsonl")
    s.add_argument("--series", help="which series, if the file has several")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dropcurve",
        description="Find where listeners drop off in serialized audio.",
    )
    p.add_argument("--version", action="version", version=f"dropcurve {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("synth", help="write a demo event log with known problems planted in it")
    s.add_argument("out", help="output file, .csv or .jsonl")
    s.add_argument("--users", type=int, default=2000)
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("--walls", type=_ints, help="paywall variants to test, e.g. 5,8,12")
    s.set_defaults(func=cmd_synth)

    s = sub.add_parser("summary", help="the headline numbers for a series")
    data_args(s)
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser("curve", help="the retention curve inside one episode")
    data_args(s)
    s.add_argument("episode", type=int)
    s.set_defaults(func=cmd_curve)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (UsageError, EventError, OSError) as e:
        print(f"dropcurve: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
