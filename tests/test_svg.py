import xml.etree.ElementTree as ET

from dropcurve.svg import bar_chart, line_chart

NS = "{http://www.w3.org/2000/svg}"


def test_line_chart_is_valid_svg_with_one_point_per_value():
    svg = ET.fromstring(line_chart([1.0, 0.8, 0.5], marks=[(0.4, "ad <break>")]))
    (line,) = svg.iter(NS + "polyline")
    points = [tuple(map(float, p.split(","))) for p in line.get("points").split()]
    assert len(points) == 3
    # Higher share = higher on the page = smaller y.
    assert points[0][1] < points[1][1] < points[2][1]
    assert any(t.text == "ad <break>" for t in svg.iter(NS + "text"))


def test_bar_chart_marks_flagged_episodes():
    svg = ET.fromstring(bar_chart([(1, 1.0), (2, 0.5), (3, 0.25)], flagged={2}))
    bars = list(svg.iter(NS + "rect"))
    assert [b.get("class") for b in bars] == ["bar", "bar flag", "bar"]
    heights = [float(b.get("height")) for b in bars]
    assert heights[0] == 2 * heights[1] == 4 * heights[2]
