from __future__ import annotations

import boost_histogram as bh

import uhi.testing.indexing


class TestAccess1D(uhi.testing.indexing.Indexing1D[bh.Histogram]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccess2D(uhi.testing.indexing.Indexing2D[bh.Histogram]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccess3D(uhi.testing.indexing.Indexing3D[bh.Histogram]):
    @classmethod
    def make_histogram(cls) -> bh.Histogram:
        return bh.Histogram(dict(cls.get_uhi()))


class TestAccessBHTag1D(TestAccess1D):
    tag = bh.tag


class TestAccessBHTag2D(TestAccess2D):
    tag = bh.tag


class TestAccessBHTag3D(TestAccess3D):
    tag = bh.tag
