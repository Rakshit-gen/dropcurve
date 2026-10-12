"""Command line entry point."""

import argparse
import dataclasses
import json
import sys
from dataclasses import replace

from . import __version__
from .anomalies import anomalies
from .binge import binge_stats, time_to_next
from .catalog import apply_catalog, load_catalog
from .cliffhanger import endings, score_endings
from .cohorts import cohorts
from .curve import retention_curve
from .episodes import episode_stats
from .events import EventError, parse_ts, read_events, write_events
from .funnel import funnel, listeners_by_episode
from .hotspots import find_hotspots
from .paywall import compare, paid_continuation, project, wall_results
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
    events = read_events(args.events)
    if args.since or args.until:
        events = (
            e
            for e in events
            if (not args.since or e.ts >= args.since) and (not args.until or e.ts < args.until)
        )
    ds = build(events)
    if args.catalog:
        apply_catalog(ds, load_catalog(args.catalog))
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


def plain(obj):
    """Dataclasses (with their computed properties), tuples and dicts as JSON values."""
    if dataclasses.is_dataclass(obj):
        out = {f.name: plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        for name, attr in vars(type(obj)).items():
            if isinstance(attr, property):
                out[name] = plain(getattr(obj, name))
        return out
    if isinstance(obj, dict):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [plain(v) for v in obj]
    if isinstance(obj, float) and obj == float("inf"):
        return None
    return obj


def emit(value) -> int:
    print(json.dumps(plain(value), indent=2))
    return 0


def span(ci: tuple[float, float]) -> str:
    return f"({100 * ci[0]:.0f}-{100 * ci[1]:.0f}%)"


def cmd_summary(args) -> int:
    ds, series = load(args)
    steps = funnel(ds, series)
    km = kaplan_meier(listeners(ds, series))
    depth = median_depth(km)
    if args.json:
        return emit(
            {
                "series": series,
                "listeners": steps[0].listeners,
                "episodes": len(steps),
                "finished_episode_1": steps[0].finished / steps[0].listeners,
                "reach_last_episode": steps[-1].reach,
                "median_depth": depth,
            }
        )
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
    if args.json:
        return emit({"series": series, "episode": args.episode, "curve": curve})
    print(f"{series} episode {args.episode}: share of starters still listening")
    print(f"  {sparkline(curve)}")
    for i in range(0, 101, 10):
        at = f"  ({mmss(duration * i / 100)})" if duration else ""
        print(f"  {i:3d}%{at}  {pct(curve[i])}")
    return 0


def cmd_episodes(args) -> int:
    ds, series = load(args)
    stats = episode_stats(ds, series)
    odd = {a.episode: a for a in anomalies(stats, min_starters=args.min_starters)}
    if args.json:
        return emit({"episodes": stats, "anomalies": list(odd.values())})
    print(" ep  starters  finished (95% range)  bounced  median heard")
    for st in stats:
        heard = "n/a" if st.median_heard is None else f"{100 * st.median_heard:.0f}%"
        line = (
            f"{st.episode:3d}  {st.starters:8d}  {pct(st.completion):>8} {span(st.ci)}"
            f"  {pct(st.bounce_rate):>7}  {heard:>12}"
        )
        if st.episode in odd:
            a = odd[st.episode]
            line += f"  low: neighbours suggest {pct(a.expected)}"
        print(line)
    return 0


def cmd_hotspots(args) -> int:
    ds, series = load(args)
    eps = [args.episode] if args.episode else ds.episodes(series)
    found = [(ep, h) for ep in eps for h in find_hotspots(ds, series, ep, factor=args.factor)]
    if args.json:
        return emit([{"episode": ep, **plain(h)} for ep, h in found])
    for ep, h in found:
        where = f"{mmss(h.seconds[0])}-{mmss(h.seconds[1])}" if h.seconds else ""
        part = f"{100 * h.start:.0f}-{100 * h.end:.0f}%"
        print(
            f"episode {ep:3d}  {part:>8} {where:>11}  lost {pct(h.drop)} of starters"
            f" ({h.excess:.0f}x the usual rate)"
        )
    if not found:
        print("no hotspots: listeners leave at a steady rate")
    return 0


def cmd_funnel(args) -> int:
    ds, series = load(args)
    steps = funnel(ds, series)
    if args.json:
        return emit(steps)
    print(" ep  listeners   reach  finished  went on to next (95% range)")
    for st in steps:
        done = st.finished / st.listeners if st.listeners else None
        if st.continuation is None:
            nxt = "-"
        else:
            nxt = f"{pct(st.continuation):>6}  {span(st.continuation_ci)}"
        print(f"{st.episode:3d}  {st.listeners:9d}  {pct(st.reach):>6}  {pct(done):>8}  {nxt}")
    return 0


def cmd_endings(args) -> int:
    ds, series = load(args)
    ends = endings(ds, series)
    score_endings(ends, min_finishers=args.min_finishers)
    if args.json:
        return emit(ends)
    print(" ep  finishers  started next within 24h  verdict")
    for e in ends:
        verdict = f"{e.verdict} (z = {e.z:.1f})" if e.verdict else ""
        print(
            f"{e.episode:3d}  {e.finishers:9d}  {pct(e.pull):>6}  {span(e.ci)}"
            f"{'':10}{verdict}".rstrip()
        )
    return 0


def cmd_survival(args) -> int:
    ds, series = load(args)
    people = listeners(ds, series, active_days=args.active_days)
    km = kaplan_meier(people)
    churned = sum(p.churned for p in people)
    if args.json:
        return emit(
            {
                "listeners": len(people),
                "lost": churned,
                "median_depth": median_depth(km),
                "table": km,
            }
        )
    print(
        f"{len(people)} listeners, {churned} gone, {len(people) - churned} still active"
        f" or caught up (counted until they stopped, not as lost)"
    )
    print(" ep  at risk  lost  still listening after it (95% range)")
    for p in km:
        print(
            f"{p.episode:3d}  {p.at_risk:7d}  {p.lost:4d}  {pct(p.survival):>6}"
            f"  {span((p.low, p.high))}"
        )
    depth = median_depth(km)
    if depth is not None:
        print(f"half of new listeners don't get past episode {depth}")
    return 0


def cmd_binge(args) -> int:
    ds, series = load(args)
    b = binge_stats(ds, series)
    gap = time_to_next(ds, series)
    if args.json:
        return emit({"sessions": b, "time_to_next": gap})
    print(f"{b.sessions} listening sessions (a gap of 30 minutes or more starts a new one)")
    print(
        f"  episodes per session    median {b.median_episodes:g},"
        f" 90th percentile {b.p90_episodes:g}"
    )
    print(f"  sessions of 3 or more   {pct(b.binge_share)}")
    if gap:
        print(
            f"  time to next episode    median {gap.median_hours * 60:.0f} min,"
            f" 90th percentile {gap.p90_hours:.1f} h ({gap.count} transitions)"
        )
    return 0


def cmd_cohorts(args) -> int:
    ds, series = load(args)
    groups = cohorts(ds, series, milestones=args.milestones)
    if args.json:
        return emit(groups)
    print("week      listeners  " + "".join(f"  {'ep ' + str(k):>6}" for k in args.milestones))
    for c in groups:
        print(
            f"{c.week}  {c.size:9d}  " + "".join(f"  {pct(c.reach[k]):>6}" for k in args.milestones)
        )
    return 0


def cmd_paywall(args) -> int:
    ds, series = load(args)
    results = wall_results(ds, series, default_free=args.free)
    if not results:
        raise UsageError(
            "no paywall variants in the data: add a free_episodes column, or pass --free"
        )
    verdict = compare(results)
    if args.json:
        return emit({"variants": results, "verdict": verdict, "summary": verdict.describe()})
    print("free eps  starters  met wall  paid  conversion (95% range)  coins per starter")
    for r in results:
        print(
            f"{r.free:8d}  {r.starters:8d}  {r.reached:8d}  {r.payers:4d}  {pct(r.conversion):>10}"
            f" {span(r.conversion_ci)}  {r.per_starter:12.2f} +- {1.96 * r.se:.2f}"
        )
    print(verdict.describe())
    if args.project:
        print_projection(ds, series, results, verdict.best)
    return 0


def print_projection(ds: Dataset, series: str, results, best) -> None:
    """Model other wall positions from what the most generous variant saw."""
    widest = max(results, key=lambda r: r.free)
    group = {u for (s, u), free in ds.walls.items() if s == series and free == widest.free}
    by_ep = listeners_by_episode(ds, series)
    reach = {
        ep: len(by_ep.get(ep, set()) & group) / widest.starters for ep in range(1, widest.free + 1)
    }
    unlocks = [c for (s, _, _), c in ds.unlocks.items() if s == series]
    q = paid_continuation(ds, series)
    if not unlocks or q is None or not best.reached:
        print("not enough paid unlocks to model other wall positions")
        return
    price = sum(unlocks) / len(unlocks)
    last = max(ds.episodes(series))
    print(
        f"\nModel, not a measurement: if conversion stayed at {pct(best.conversion)} and payers"
        f" kept unlocking at {pct(q)}, at {price:.0f} coins an episode:"
    )
    for p in project(reach, last, best.conversion, q, price, range(1, widest.free)):
        print(
            f"  wall after episode {p.free:2d}  reaches {pct(p.reach):>6}"
            f"  ~{p.coins_per_starter:.2f} coins per starter"
        )


def cmd_synth(args) -> int:
    truth = Truth.demo()
    if args.walls:
        truth = replace(truth, walls=args.walls)
    n = write_events(generate(args.users, truth, seed=args.seed), args.out)
    print(f"wrote {n} events from {args.users} listeners to {args.out}")
    return 0


def when(text: str):
    try:
        return parse_ts(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a date like 2026-02-01, got {text!r}") from None


def data_args(s: argparse.ArgumentParser) -> None:
    s.add_argument("events", help="event log, .csv or .jsonl")
    s.add_argument("--series", help="which series, if the file has several")
    s.add_argument("--json", action="store_true", help="print JSON instead of a table")
    s.add_argument("--catalog", help="CSV of series,episode,duration for players without lengths")
    s.add_argument("--since", type=when, help="only events at or after this time (ISO date)")
    s.add_argument("--until", type=when, help="only events before this time (ISO date)")


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

    s = sub.add_parser("episodes", help="completion and bounce per episode, flagging odd ones")
    data_args(s)
    s.add_argument(
        "--min-starters",
        type=int,
        default=50,
        help="don't flag episodes with fewer starters than this (50)",
    )
    s.set_defaults(func=cmd_episodes)

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

    s = sub.add_parser("binge", help="episodes per sitting and time between episodes")
    data_args(s)
    s.set_defaults(func=cmd_binge)

    s = sub.add_parser("cohorts", help="how far people get, by the week they arrived")
    data_args(s)
    s.add_argument(
        "--milestones",
        type=_ints,
        default=(2, 3, 5, 10),
        help="episodes to show reach for (2,3,5,10)",
    )
    s.set_defaults(func=cmd_cohorts)

    s = sub.add_parser("paywall", help="compare free-episode variants by coins per new listener")
    data_args(s)
    s.add_argument(
        "--free", type=int, help="free episodes for listeners the data doesn't say (no test)"
    )
    s.add_argument(
        "--project", action="store_true", help="also model wall positions that weren't tested"
    )
    s.set_defaults(func=cmd_paywall)
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
