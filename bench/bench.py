"""Time the full pipeline on a synthetic log.

    uv run python bench/bench.py [listeners]

Writes the log to a temp dir, then times reading it, building views, and
writing the HTML report. Prints peak memory too. Numbers depend on the
machine; the README says which one they came from.
"""

import os
import platform
import resource
import sys
import tempfile
import time

from dropcurve.events import read_events, write_events
from dropcurve.report import html_report
from dropcurve.synth import Truth, generate
from dropcurve.views import build


def main() -> None:
    users = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    truth = Truth.demo()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "events.csv")
        events = write_events(generate(users, truth), path)
        size = os.path.getsize(path) / 1e6

        t0 = time.perf_counter()
        ds = build(read_events(path))
        t1 = time.perf_counter()
        html_report(ds, truth.series)
        t2 = time.perf_counter()

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = rss / 1e6 if sys.platform == "darwin" else rss / 1e3  # bytes on macOS, KB on Linux
    print(f"{platform.machine()} {platform.system()}, Python {platform.python_version()}")
    print(f"{users} listeners, {events} events, {size:.1f} MB CSV, {len(ds.views)} views")
    print(f"read + build views  {t1 - t0:6.2f} s  ({events / (t1 - t0):,.0f} events/s)")
    print(f"full HTML report    {t2 - t1:6.2f} s")
    print(f"peak memory         {rss_mb:6.0f} MB (includes generating the log)")


if __name__ == "__main__":
    main()
