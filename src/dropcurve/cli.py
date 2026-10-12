"""Command line entry point."""

import argparse
import sys
from dataclasses import replace

from . import __version__
from .events import write_events
from .synth import Truth, generate


def _ints(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in text.split(",") if x.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected numbers like 5,8,12, got {text!r}") from None


def cmd_synth(args) -> int:
    truth = Truth.demo()
    if args.walls:
        truth = replace(truth, walls=args.walls)
    n = write_events(generate(args.users, truth, seed=args.seed), args.out)
    print(f"wrote {n} events from {args.users} listeners to {args.out}")
    return 0


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
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
