from __future__ import annotations

import boost_histogram as bh
import numpy as np

import uhi.testing.indexing


class TestAccess(uhi.testing.indexing.Indexing[bh.Histogram]):
    @staticmethod
    def make_histogram_1() -> bh.Histogram:
        h1 = bh.Histogram(bh.axis.Regular(10, 0, 1))
        h1[:] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        h1[bh.overflow] = 1
        return h1

    @staticmethod
    def make_histogram_3() -> bh.Histogram:
        h3 = bh.Histogram(
            bh.axis.Regular(2, 0, 2),
            bh.axis.Regular(5, 0, 5),
            bh.axis.Regular(10, 0, 10),
        )
        x, y, z = np.mgrid[0:2, 0:5, 0:10]
        h3[...] = x + 2 * y + 3 * z
        return h3


class TestAccessBHTag(TestAccess):
    tag = bh.tag
