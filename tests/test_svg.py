import xml.etree.ElementTree as ET

from dropcurve.svg import line_chart

NS = "{http://www.w3.org/2000/svg}"


def test_line_chart_is_valid_svg_with_one_point_per_value():
    svg = ET.fromstring(line_chart([1.0, 0.8, 0.5], marks=[(0.4, "ad <break>")]))
    (line,) = svg.iter(NS + "polyline")
    points = [tuple(map(float, p.split(","))) for p in line.get("points").split()]
    assert len(points) == 3
    # Higher share = higher on the page = smaller y.
    assert points[0][1] < points[1][1] < points[2][1]
    assert any(t.text == "ad <break>" for t in svg.iter(NS + "text"))
