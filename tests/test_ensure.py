from __future__ import annotations

import numpy as np
import pytest
from pytest import approx

from uhi.numpy_plottable import ensure_plottable_histogram


def test_from_numpy() -> None:
    hist1 = ((1, 2, 3, 4, 1, 2), (0, 1, 2, 3))

    h = ensure_plottable_histogram(hist1)

    assert h.values() == approx(np.array(hist1[0]))
    assert len(h.axes) == 1
    assert len(h.axes[0]) == 3
    assert h.axes[0][0] == (0.0, 1.0)
    assert h.axes[0][1] == (1.0, 2.0)
    assert h.axes[0][2] == (2.0, 3.0)


def test_from_numpy_2d() -> None:
    np.random.seed(42)
    x = np.random.normal(1, 2, 1000)
    y = np.random.normal(-1, 1, 1000)
    result = np.histogram2d(x, y)

    h = ensure_plottable_histogram(result)

    assert h.values() == approx(result[0])
    assert len(h.axes) == 2
    assert len(h.axes[0]) == 10
    assert h.axes[0][0] == approx(result[1][0:2])
    assert h.axes[0][1] == approx(result[1][1:3])
    assert h.axes[1][0] == approx(result[2][0:2])
    assert h.axes[1][1] == approx(result[2][1:3])


def test_from_numpy_dd() -> None:
    np.random.seed(42)
    x = np.random.normal(1, 2, 1000)
    y = np.random.normal(-1, 1, 1000)
    z = np.random.normal(3, 3, 1000)
    result = np.histogramdd((x, y, z))

    h = ensure_plottable_histogram(result)

    assert h.values() == approx(result[0])
    assert len(h.axes) == 3
    assert len(h.axes[0]) == 10
    assert h.axes[0][0] == approx(result[1][0][0:2])
    assert h.axes[0][1] == approx(result[1][0][1:3])
    assert h.axes[1][0] == approx(result[1][1][0:2])
    assert h.axes[1][1] == approx(result[1][1][1:3])
    assert h.axes[2][0] == approx(result[1][2][0:2])
    assert h.axes[2][1] == approx(result[1][2][1:3])


def test_from_bh_regular() -> None:
    bh = pytest.importorskip("boost_histogram")
    h1 = bh.Histogram(bh.axis.Regular(5, 0, 5))
    h1[...] = (3, 2, 1, 2, 3)

    h = ensure_plottable_histogram(h1)

    assert h is h1

    assert h.values() == approx(np.array((3, 2, 1, 2, 3)))
    assert len(h.axes) == 1
    assert len(h.axes[0]) == 5
    assert h.axes[0][0] == approx(np.array((0, 1)))
    assert h.axes[0][1] == approx(np.array((1, 2)))
    assert h.axes[0][2] == approx(np.array((2, 3)))


def test_from_bh_integer() -> None:
    bh = pytest.importorskip("boost_histogram")
    h1 = bh.Histogram(bh.axis.Integer(1, 6))
    h1[...] = (3, 2, 1, 2, 3)

    h = ensure_plottable_histogram(h1)

    assert h is h1

    assert h.values() == approx(np.array((3, 2, 1, 2, 3)))
    assert len(h.axes) == 1
    assert len(h.axes[0]) == 5
    assert h.axes[0][0] == 1
    assert h.axes[0][1] == 2
    assert h.axes[0][2] == 3


def test_from_numpy_stacked() -> None:
    """Regression test for issue #233.

    A tuple of (list_of_value_arrays, bin_edges) — a stacked histogram format
    used by histoprint — was mishandled: the list was converted to a 2D array
    but only one bin dimension was supplied, causing zip() to raise ValueError.
    """
    rng = np.random.default_rng(42)
    bins = np.linspace(-5, 5, 16)  # 15 bins → 16 edges
    values = [rng.integers(0, 300, size=15) for _ in range(3)]
    hist = (values, bins)

    h = ensure_plottable_histogram(hist)

    assert h.values() == approx(np.asarray(values))
    assert len(h.axes) == 1
    assert len(h.axes[0]) == 15
    assert h.axes[0][0] == approx(bins[0:2])
    assert h.axes[0][-1] == approx(bins[-2:])


def test_from_numpy_excess_bins_raises() -> None:
    """If more bin arrays are provided than histogram dimensions, raise.

    This exercises the new guard that prevents passing e.g. two bin arrays
    for a 1-D values array.
    """
    values = np.arange(5)
    bins1 = np.linspace(0, 5, 6)
    bins2 = np.linspace(0, 5, 6)
    # Provide two bin arrays for a 1-D histogram
    hist = (values, (bins1, bins2))

    with pytest.raises(ValueError, match="Too many bin arrays"):
        ensure_plottable_histogram(hist)


def test_from_numpy_mixed_none_bins() -> None:
    """Mixed None entries in a standard tuple should use the default integer axis.

    A tuple like (vals, edges0, None) was broken: np.asarray(None) produced a
    0-d object array, which bypassed _bin_helper's ``bins is None`` check and
    raised ValueError.  The fix preserves None values so _bin_helper produces
    a 0..N integer-edges axis for those dimensions.
    """
    values = np.zeros((3, 4))
    edges0 = np.array([0.0, 1.0, 2.0, 3.0])
    hist = (values, edges0, None)

    h = ensure_plottable_histogram(hist)

    assert h.values() == approx(values)
    assert len(h.axes) == 2
    # Axis 0 should use the provided edges
    assert len(h.axes[0]) == 3
    assert h.axes[0][0] == approx((0.0, 1.0))
    assert h.axes[0][2] == approx((2.0, 3.0))
    # Axis 1 should be the default integer axis (0..N)
    assert len(h.axes[1]) == 4
    assert h.axes[1][0] == approx((0.0, 1.0))
    assert h.axes[1][3] == approx((3.0, 4.0))


def test_axis_eq_non_axis_object() -> None:
    """Comparing a NumPyPlottableAxis to a non-axis object must not raise.

    __eq__ should return NotImplemented (which Python reflects to False) when
    the other side has no .edges attribute.
    """
    from uhi.numpy_plottable import NumPyPlottableAxis

    edges = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]])
    axis = NumPyPlottableAxis(edges)

    # Must not raise — Python reflects NotImplemented to False
    assert (axis == "foo") is False
    assert (axis == 42) is False
    assert (axis == None) is False  # noqa: E711


def test_axis_eq_different_shape() -> None:
    """Comparing axes with different numbers of bins should return False, not raise."""
    from uhi.numpy_plottable import NumPyPlottableAxis

    edges_3 = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]])
    edges_4 = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    axis_3 = NumPyPlottableAxis(edges_3)
    axis_4 = NumPyPlottableAxis(edges_4)

    assert axis_3 != axis_4


def test_from_bh_str_cat() -> None:
    bh = pytest.importorskip("boost_histogram")
    h1 = bh.Histogram(bh.axis.StrCategory(["hi", "ho"]))
    h1.fill(["hi", "hi", "hi", "ho"])

    h = ensure_plottable_histogram(h1)

    assert h is h1

    assert h.values() == approx(np.array((3, 1)))
    assert len(h.axes) == 1
    assert len(h.axes[0]) == 2

    assert h.axes[0][0] == "hi"
    assert h.axes[0][1] == "ho"
