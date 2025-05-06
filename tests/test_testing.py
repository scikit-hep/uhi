from __future__ import annotations

import boost_histogram as bh
import numpy as np

import uhi.testing.indexing


class TestAccess1D(uhi.testing.indexing.Indexing1D[bh.Histogram]):
    @staticmethod
    def make_histogram() -> bh.Histogram:
        h = bh.Histogram(bh.axis.Regular(10, 0, 1))
        h[:] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        h[bh.underflow] = 3
        h[bh.overflow] = 1
        return h


class TestAccess2D(uhi.testing.indexing.Indexing2D[bh.Histogram]):
    @staticmethod
    def make_histogram() -> bh.Histogram:
        h = bh.Histogram(
            bh.axis.Regular(2, 0, 2),
            bh.axis.Regular(5, 0, 5),
        )
        x, y = np.mgrid[0:2, 0:5]
        h[...] = x + 2 * y
        return h


class TestAccess3D(uhi.testing.indexing.Indexing3D[bh.Histogram]):
    @staticmethod
    def make_histogram() -> bh.Histogram:
        h = bh.Histogram(
            bh.axis.Regular(2, 0, 2),
            bh.axis.Regular(5, 0, 5),
            bh.axis.Regular(10, 0, 10),
        )
        x, y, z = np.mgrid[0:2, 0:5, 0:10]
        h[...] = x + 2 * y + 3 * z
        return h


class TestAccessBHTag1D(TestAccess1D):
    tag = bh.tag


class TestAccessBHTag2D(TestAccess2D):
    tag = bh.tag


class TestAccessBHTag3D(TestAccess3D):
    tag = bh.tag
