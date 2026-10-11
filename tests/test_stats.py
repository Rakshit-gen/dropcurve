import pytest

from dropcurve.stats import median, quantile, two_proportion_z, wilson


def test_wilson_known_value():
    lo, hi = wilson(50, 100)
    assert lo == pytest.approx(0.4038, abs=1e-4)
    assert hi == pytest.approx(0.5962, abs=1e-4)


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(0, 20)
    assert lo == 0.0 and 0 < hi < 0.2
    lo, hi = wilson(20, 20)
    assert hi == 1.0 and lo > 0.8


def test_z():
    assert two_proportion_z(60, 100, 40, 100) == pytest.approx(2.828, abs=1e-3)
    assert two_proportion_z(0, 0, 1, 2) == 0.0
    assert two_proportion_z(5, 5, 5, 5) == 0.0


def test_median_and_quantile():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 2, 3]) == 2.5
    assert quantile([1, 2, 3, 4, 5], 0.9) == pytest.approx(4.6)
