"""One self-contained HTML page with the findings for a series."""

from html import escape

from .anomalies import anomalies
from .cliffhanger import endings, score_endings
from .curve import retention_curve
from .episodes import episode_stats
from .funnel import funnel
from .hotspots import find_hotspots
from .paywall import compare, wall_results
from .survival import kaplan_meier, listeners, median_depth
from .svg import bar_chart, line_chart
from .views import Dataset

STYLE = """
:root { --bg: #fbfaf7; --fg: #1d1d1b; --muted: #6b6a66; --line: #1f5f8b;
        --flag: #b4462b; --grid: #e4e1da; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161615; --fg: #ecebe6; --muted: #9a9890; --line: #6fb3e0;
          --flag: #e5826a; --grid: #2c2b29; }
}
body { background: var(--bg); color: var(--fg); margin: 0 auto; padding: 24px 16px 64px;
       max-width: 760px; font: 16px/1.5 system-ui, sans-serif; }
h1 { font-size: 1.6rem; margin-bottom: 0; }
h2 { font-size: 1.15rem; margin-top: 2.2rem; border-bottom: 1px solid var(--grid); }
.meta, .note { color: var(--muted); font-size: 0.9rem; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 4px 8px 4px 0; border-bottom: 1px solid var(--grid); }
svg { width: 100%; height: auto; }
svg .grid { stroke: var(--grid); }
svg .tick { fill: var(--muted); font-size: 11px; }
svg .line { stroke: var(--line); stroke-width: 2; }
svg .mark { stroke: var(--flag); stroke-dasharray: 4 3; }
svg .bar { fill: var(--line); }
svg .bar.flag { fill: var(--flag); }
"""


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def _table(head: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def html_report(ds: Dataset, series: str, source: str = "") -> str:
    steps = funnel(ds, series)
    stats = episode_stats(ds, series)
    odd = anomalies(stats)
    ends = endings(ds, series)
    score_endings(ends)
    weak = [e for e in ends if e.verdict == "weak"]
    depth = median_depth(kaplan_meier(listeners(ds, series)))
    hot = [(ep, h) for ep in ds.episodes(series) for h in find_hotspots(ds, series, ep)]

    out = [
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{escape(series)} drop-off</title><style>{STYLE}</style></head><body>",
        f"<h1>{escape(series)}</h1>",
        f"<p class='meta'>{steps[0].listeners} listeners, {len(steps)} episodes"
        + (f", from {escape(source)}" if source else "")
        + "</p>",
        "<h2>How far people get</h2>",
        bar_chart(
            [(s.episode, s.reach) for s in steps],
            x_label="episode",
            flagged={a.episode for a in odd} | {e.episode for e in weak},
        ),
        "<p class='note'>Share of new listeners who started each episode."
        " Red bars are episodes flagged below.",
    ]
    if depth is not None:
        out.append(f" Half of new listeners don't get past episode {depth}.")
    out.append("</p><h2>What to look at</h2>")

    rows = []
    for ep, h in sorted(hot, key=lambda p: -p[1].drop)[:8]:
        where = f"{mmss(h.seconds[0])}-{mmss(h.seconds[1])}" if h.seconds else f"{h.start:.0%}"
        rows.append([f"episode {ep}", f"drop at {where}", f"{pct(h.drop)} of starters leave"])
    for e in weak:
        rows.append(
            [f"episode {e.episode}", "weak ending", f"{pct(e.pull)} start the next one in 24h"]
        )
    for a in odd:
        rows.append(
            [
                f"episode {a.episode}",
                "low completion",
                f"{pct(a.completion)}, neighbours suggest {pct(a.expected)}",
            ]
        )
    out.append(_table(["where", "what", "how big"], rows) if rows else "<p>Nothing stands out.</p>")

    for ep in sorted({1} | {ep for ep, _ in hot}):
        curve = retention_curve(ds, series, ep)
        if not curve:
            continue
        marks = [(h.start, mmss(h.seconds[0]) if h.seconds else "") for e, h in hot if e == ep]
        out.append(f"<h2>Inside episode {ep}</h2>")
        out.append(line_chart(curve, x_label="share of the episode", marks=marks))

    walls = wall_results(ds, series)
    if walls:
        verdict = compare(walls)
        out.append("<h2>Paywall test</h2>")
        out.append(
            _table(
                ["free episodes", "new listeners", "paid", "conversion", "coins per listener"],
                [
                    [w.free, w.starters, w.payers, pct(w.conversion), f"{w.per_starter:.2f}"]
                    for w in walls
                ],
            )
        )
        out.append(f"<p>{escape(verdict.describe())}.</p>")

    out.append("</body></html>")
    return "\n".join(out)
