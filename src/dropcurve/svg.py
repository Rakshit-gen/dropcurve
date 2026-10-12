"""Small inline SVG charts for the HTML report. No plotting library needed."""

from html import escape

PAD_LEFT, PAD_BOTTOM, PAD_TOP, PAD_RIGHT = 44, 24, 10, 10


def line_chart(
    values: list[float],
    width: int = 640,
    height: int = 220,
    x_label: str = "",
    marks: list[tuple[float, str]] = (),
) -> str:
    """values are shares (0..1) at evenly spaced x positions from 0 to 1.

    `marks` are (x, text) pairs drawn as dashed vertical lines, e.g. hotspots.
    """
    w = width - PAD_LEFT - PAD_RIGHT
    h = height - PAD_TOP - PAD_BOTTOM
    n = max(len(values) - 1, 1)

    def x(i: float) -> float:
        return PAD_LEFT + w * i

    def y(v: float) -> float:
        return PAD_TOP + h * (1 - v)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(x_label)}">'
    ]
    for v in (0, 0.25, 0.5, 0.75, 1):
        parts.append(
            f'<line class="grid" x1="{PAD_LEFT}" x2="{PAD_LEFT + w}" y1="{y(v):.1f}" '
            f'y2="{y(v):.1f}"/><text class="tick" x="{PAD_LEFT - 6}" y="{y(v) + 4:.1f}" '
            f'text-anchor="end">{int(v * 100)}%</text>'
        )
    for at, text in marks:
        parts.append(
            f'<line class="mark" x1="{x(at):.1f}" x2="{x(at):.1f}" y1="{PAD_TOP}" '
            f'y2="{PAD_TOP + h}"/><text class="tick" x="{x(at) + 4:.1f}" y="{PAD_TOP + 12}">'
            f"{escape(text)}</text>"
        )
    points = " ".join(f"{x(i / n):.1f},{y(v):.1f}" for i, v in enumerate(values))
    parts.append(f'<polyline class="line" fill="none" points="{points}"/>')
    if x_label:
        parts.append(
            f'<text class="tick" x="{PAD_LEFT + w / 2:.1f}" y="{height - 4}" '
            f'text-anchor="middle">{escape(x_label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
