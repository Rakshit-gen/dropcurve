import pytest
from factory import ev

from dropcurve.catalog import apply_catalog, load_catalog
from dropcurve.events import EventError
from dropcurve.views import build


def test_catalog_fills_and_overrides(tmp_path):
    p = tmp_path / "catalog.csv"
    p.write_text("series,episode,duration\ns1,1,400\ns1,2,800\n")
    ds = build([ev("u1", 1, 200, duration=600), ev("u1", 2, 200, duration=None)])
    apply_catalog(ds, load_catalog(p))
    assert ds.durations == {("s1", 1): 400, ("s1", 2): 800}
    assert ds.completion(ds.views[("s1", "u1", 2)]) == 0.25


def test_bad_catalog(tmp_path):
    p = tmp_path / "catalog.csv"
    p.write_text("series,episode\ns1,1\n")
    with pytest.raises(EventError, match="needs columns"):
        load_catalog(p)
