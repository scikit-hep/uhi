import numpy as np
import pytest
from pytest import approx

from uhi.numpy_plottable import ensure_plottable_histogram

ROOT = pytest.importorskip("ROOT")


def test_root_imported() -> None:
    assert ROOT.TString("hi") == "hi"


def test_root_th1f_convert() -> None:
    th = ROOT.TH1F("h1", "h1", 50, -2.5, 2.5)
    th.FillRandom("gaus", 10000)
    h = ensure_plottable_histogram(th)
    assert all(th.GetBinContent(i + 1) == approx(iv) for i, iv in enumerate(h.values()))
    assert all(
        th.GetBinError(i + 1) == approx(ie)
        for i, ie in enumerate(np.sqrt(h.variances()))  # type: ignore[arg-type]
    )


def test_root_th2f_convert() -> None:
    th = ROOT.TH2F("h2", "h2", 50, -2.5, 2.5, 50, -2.5, 2.5)
    _ = ROOT.TF2("xyg", "xygaus", -2.5, 2.5, -2.5, 2.5)
    th.FillRandom("xyg", 10000)
    h = ensure_plottable_histogram(th)
    assert all(
        th.GetBinContent(i + 1, j + 1) == approx(iv)
        for i, row in enumerate(h.values())
        for j, iv in enumerate(row)
    )
    assert all(
        th.GetBinError(i + 1, j + 1) == approx(ie)
        for i, row in enumerate(np.sqrt(h.variances()))  # type: ignore[arg-type]
        for j, ie in enumerate(row)
    )
