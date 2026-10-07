from __future__ import annotations

from typing import Any

import boost_histogram as bh
import numpy as np

import uhi.testing.indexing
from uhi.typing.serialization import HistogramIR


class TestAccess1D(uhi.testing.indexing.Indexing1D[bh.Histogram[bh.storage.Double]]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Double]:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccess2D(uhi.testing.indexing.Indexing2D[bh.Histogram[bh.storage.Double]]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Double]:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccess3D(uhi.testing.indexing.Indexing3D[bh.Histogram[bh.storage.Double]]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Double]:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccessBHTag1D(TestAccess1D):
    tag = bh.tag


class TestAccessBHTag2D(TestAccess2D):
    tag = bh.tag


class TestAccessBHTag3D(TestAccess3D):
    tag = bh.tag


WEIGHT_DTYPE = np.dtype([("value", "f8"), ("variance", "f8")])


def make_weighted(ir: HistogramIR) -> bh.Histogram[bh.storage.Weight]:
    h: bh.Histogram[bh.storage.Double] = bh.Histogram(dict(ir))
    weighted = bh.Histogram(*h.axes, storage=bh.storage.Weight())
    weighted.view(flow=True).value = h.values(flow=True)
    weighted.view(flow=True).variance = h.values(flow=True)
    return weighted


class WeightMixin(uhi.testing.indexing.Indexing):
    """Run the suites with a storage whose bins are not plain numbers."""

    def bin_to_value(self, bin: Any) -> Any:
        return bin.value

    def value_to_bin(self, value: Any) -> Any:
        return np.array((value, value), dtype=WEIGHT_DTYPE)

    def sum_to_value(self, bin: Any) -> Any:
        if isinstance(bin, bh.Histogram):
            total: Any = bin.sum(flow=True)
            return total.value
        return bin.value


class TestAccessWeight1D(
    WeightMixin, uhi.testing.indexing.Indexing1D[bh.Histogram[bh.storage.Weight]]
):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Weight]:
        return make_weighted(cls.get_uhi())


class TestAccessWeight2D(
    WeightMixin, uhi.testing.indexing.Indexing2D[bh.Histogram[bh.storage.Weight]]
):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Weight]:
        return make_weighted(cls.get_uhi())


class TestAccessWeight3D(
    WeightMixin, uhi.testing.indexing.Indexing3D[bh.Histogram[bh.storage.Weight]]
):
    @classmethod
    def make_histogram(cls) -> bh.Histogram[bh.storage.Weight]:
        return make_weighted(cls.get_uhi())
