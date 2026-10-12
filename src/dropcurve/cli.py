"""Command line entry point."""

import argparse
import sys
from dataclasses import replace

from . import __version__
from .cliffhanger import endings, score_endings
from .curve import retention_curve
from .events import EventError, read_events, write_events
from .funnel import funnel
from .hotspots import find_hotspots
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


def cmd_hotspots(args) -> int:
    ds, series = load(args)
    eps = [args.episode] if args.episode else ds.episodes(series)
    found = 0
    for ep in eps:
        for h in find_hotspots(ds, series, ep, factor=args.factor):
            where = f"{mmss(h.seconds[0])}-{mmss(h.seconds[1])}" if h.seconds else ""
            span = f"{100 * h.start:.0f}-{100 * h.end:.0f}%"
            print(
                f"episode {ep:3d}  {span:>8} {where:>11}  lost {pct(h.drop)} of starters"
                f" ({h.excess:.0f}x the usual rate)"
            )
            found += 1
    if not found:
        print("no hotspots: listeners leave at a steady rate")
    return 0


def cmd_funnel(args) -> int:
    ds, series = load(args)
    print(" ep  listeners   reach  finished  went on to next (95% range)")
    for st in funnel(ds, series):
        done = st.finished / st.listeners if st.listeners else None
        if st.continuation is None:
            nxt = "-"
        else:
            lo, hi = st.continuation_ci
            nxt = f"{pct(st.continuation):>6}  ({100 * lo:.0f}-{100 * hi:.0f}%)"
        print(f"{st.episode:3d}  {st.listeners:9d}  {pct(st.reach):>6}  {pct(done):>8}  {nxt}")
    return 0


def cmd_endings(args) -> int:
    ds, series = load(args)
    ends = endings(ds, series)
    score_endings(ends, min_finishers=args.min_finishers)
    print(" ep  finishers  started next within 24h  verdict")
    for e in ends:
        lo, hi = e.ci
        verdict = f"{e.verdict} (z = {e.z:.1f})" if e.verdict else ""
        print(
            f"{e.episode:3d}  {e.finishers:9d}  {pct(e.pull):>6}  ({100 * lo:.0f}-{100 * hi:.0f}%)"
            f"{'':10}{verdict}".rstrip()
        )
    return 0


def cmd_survival(args) -> int:
    ds, series = load(args)
    people = listeners(ds, series, active_days=args.active_days)
    km = kaplan_meier(people)
    churned = sum(p.churned for p in people)
    print(
        f"{len(people)} listeners, {churned} gone, {len(people) - churned} still active"
        f" or caught up (counted until they stopped, not as lost)"
    )
    print(" ep  at risk  lost  still listening after it (95% range)")
    for p in km:
        print(
            f"{p.episode:3d}  {p.at_risk:7d}  {p.lost:4d}  {pct(p.survival):>6}"
            f"  ({100 * p.low:.0f}-{100 * p.high:.0f}%)"
        )
    depth = median_depth(km)
    if depth is not None:
        print(f"half of new listeners don't get past episode {depth}")
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

    s = sub.add_parser("hotspots", help="moments where listeners leave much faster than usual")
    data_args(s)
    s.add_argument("--episode", type=int, help="only this episode")
    s.add_argument(
        "--factor", type=float, default=3.0, help="how many times the usual loss rate (3)"
    )
    s.set_defaults(func=cmd_hotspots)

    s = sub.add_parser("funnel", help="how far into the series people get")
    data_args(s)
    s.set_defaults(func=cmd_funnel)

    s = sub.add_parser("endings", help="which episode endings pull people into the next one")
    data_args(s)
    s.add_argument(
        "--min-finishers",
        type=int,
        default=30,
        help="don't judge an ending with fewer finishers than this (30)",
    )
    s.set_defaults(func=cmd_endings)

    s = sub.add_parser("survival", help="Kaplan-Meier: how deep new listeners get")
    data_args(s)
    s.add_argument(
        "--active-days",
        type=float,
        default=7.0,
        help="seen this recently = still active, not lost (7)",
    )
    s.set_defaults(func=cmd_survival)
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
