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
    assert h.axes[0][0] == (0, 1)
    assert h.axes[0][1] == (1, 2)
    assert h.axes[0][2] == (2, 3)


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
