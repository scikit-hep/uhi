from __future__ import annotations

import abc
import typing
import unittest
from typing import Any

import uhi.tag

T = typing.TypeVar("T", bound=Any)

__all__ = ["Indexing"]


def __dir__() -> list[str]:
    return __all__


class Indexing(typing.Generic[T], abc.ABC, unittest.TestCase):
    """
    This test requires histograms to be created first.

    h1 and h3 are histograms created in the test suite.
    h1 is a 1D histogram with 10 bins from 0 to 1. Each bin has 2 more than the
    one before, starting with 0. The overflow bin has 1.

    h3 is a 3D histogram with [2,5,10] bins. The contents are x+2y+3z, where x,
    y, and z are the bin indices.
    """

    h1: T
    h3: T
    tag = uhi.tag

    @staticmethod
    @abc.abstractmethod
    def make_histogram_1() -> T:
        pass

    @staticmethod
    @abc.abstractmethod
    def make_histogram_3() -> T:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.h1 = cls.make_histogram_1()
        cls.h3 = cls.make_histogram_3()

    def test_access_integer_1d(self) -> None:
        for i in range(10):
            with self.subTest(i=i):
                self.assertEqual(self.h1[i], 2 * i)

        with self.assertRaises(IndexError):
            self.h1[10]

        self.assertEqual(self.h1[-1], 18)

    def test_access_integer_1d_flow(self) -> None:
        self.assertEqual(self.h1[self.tag.overflow], 1)
        self.assertEqual(self.h1[self.tag.underflow], 0)

    def test_access_integer_3d(self) -> None:
        for i in range(2):
            for j in range(5):
                for k in range(10):
                    with self.subTest(i=i, j=j, k=k):
                        self.assertEqual(self.h3[i, j, k], i + 2 * j + 3 * k)

        with self.assertRaises(IndexError):
            self.h3[2, 0, 0]
        with self.assertRaises(IndexError):
            self.h3[0, 5, 0]
        with self.assertRaises(IndexError):
            self.h3[0, 0, 10]

        self.assertEqual(self.h3[-1, -1, -1], 36)

    def test_access_loc_1d(self) -> None:
        self.assertEqual(self.h1[self.tag.loc(0.05)], 0)
        self.assertEqual(self.h1[self.tag.loc(0.15)], 2)
        self.assertEqual(self.h1[self.tag.loc(0.95)], 18)
        self.assertEqual(self.h1[self.tag.loc(-1)], 0)
        self.assertEqual(self.h1[self.tag.loc(2)], 1)

    def test_access_loc_3d(self) -> None:
        self.assertEqual(
            self.h3[self.tag.loc(0.5), self.tag.loc(0.5), self.tag.loc(0.5)], 0
        )
        self.assertEqual(
            self.h3[self.tag.loc(0.5), self.tag.loc(1.5), self.tag.loc(0.5)], 2
        )
        self.assertEqual(
            self.h3[self.tag.loc(0.5), self.tag.loc(4.5), self.tag.loc(9.5)], 35
        )
        self.assertEqual(
            self.h3[self.tag.loc(-1), self.tag.loc(0.5), self.tag.loc(0.5)], 0
        )

    def test_access_loc_3d_mixed(self) -> None:
        self.assertEqual(self.h3[self.tag.loc(0.5), 0, self.tag.loc(0.5)], 0)
        self.assertEqual(self.h3[0, self.tag.loc(1.5), self.tag.loc(0.5)], 2)
        self.assertEqual(self.h3[self.tag.loc(0.5), self.tag.loc(4.5), 9], 35)
        self.assertEqual(self.h3[1, self.tag.loc(4.5), 9], 36)

    def test_access_loc_addition(self) -> None:
        self.assertEqual(self.h1[self.tag.loc(0.05) + 1], 2)
        self.assertEqual(self.h1[self.tag.loc(0.55) + 2], 14)
        self.assertEqual(self.h1[self.tag.loc(0.55) - 2], 6)

    def test_slicing_all(self) -> None:
        self.assertEqual(self.h1[:], self.h1)
        self.assertEqual(self.h1[...], self.h1)
        self.assertEqual(self.h3[:, :, :], self.h3)
        self.assertEqual(self.h3[...], self.h3)
        self.assertEqual(self.h3[:, ...], self.h3)
        self.assertEqual(self.h3[..., :], self.h3)

    def test_slicing_1d_closed(self) -> None:
        h = self.h1[2:4]
        self.assertEqual(h[self.tag.underflow], 2)
        self.assertEqual(h[0], 4)
        self.assertEqual(h[1], 6)
        self.assertEqual(h[self.tag.overflow], 79)

        with self.assertRaises(IndexError):
            h[2]

    def test_slicing_1d_open_upper(self) -> None:
        h = self.h1[5:]
        self.assertEqual(h[self.tag.underflow], 20)
        self.assertEqual(h[0], 10)
        self.assertEqual(h[4], 18)
        self.assertEqual(h[self.tag.overflow], 1)
        with self.assertRaises(IndexError):
            h[5]

    def test_slicing_1d_open_lower(self) -> None:
        h = self.h1[:5]
        self.assertEqual(h[self.tag.underflow], 0)
        self.assertEqual(h[0], 0)
        self.assertEqual(h[4], 8)
        self.assertEqual(h[self.tag.overflow], 71)
        with self.assertRaises(IndexError):
            h[5]
