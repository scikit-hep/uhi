from __future__ import annotations

import abc
import typing
import unittest
from typing import Any

import numpy as np

import uhi.tag
from uhi.typing.serialization import HistogramIR

T = typing.TypeVar("T", bound=Any)

__all__ = ["Indexing1D", "Indexing3D"]


if typing.TYPE_CHECKING:
    # This is a workaround for the issue with type checkers
    # and generics with custom __getitem__ methods.
    sum = 42


def __dir__() -> list[str]:
    return __all__


class Indexing(abc.ABC, unittest.TestCase):
    """
    This super class provides the basic structure for indexing tests.
    """

    def bin_to_value(self, bin: Any) -> Any:
        """
        Allow downstream classes to handle more complex bin objects.
        """
        return bin

    def value_to_bin(self, value: Any) -> Any:
        """
        Inverse of bin_to_value, for downstream classes with complex bins.
        """
        return value

    def values_to_bins(self, values: Any) -> Any:
        """
        Loops over values and converts them to bins using value_to_bin.
        """
        return [self.value_to_bin(v) for v in values]

    def sum_to_value(self, bin: Any) -> Any:
        """
        Allow downstream classes to handle more summed bin objects. E.g. it can be a projection from a Histo2D to Histo1D.
        """
        return bin

    def assertEqualBinValue(self, bin: Any, value: Any) -> None:
        self.assertEqual(self.bin_to_value(bin), value)

    def assertEqualSum(self, bin: Any, value: Any) -> None:
        self.assertEqual(self.sum_to_value(bin), value)


class Indexing1D(typing.Generic[T], Indexing):
    """
    This test requires a histogram to be created first.

    h is a 1D histogram with 10 bins from 0 to 1. Each bin has 2 more than the
    one before, starting with 0. The overflow bin has 1. The underflow bin has 3.
    You can access the UHI serialized version with `.uhi`.
    """

    h: T
    tag = uhi.tag

    @staticmethod
    def get_uhi() -> HistogramIR:
        return {
            "uhi_schema": 1,
            "axes": [
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 1.0,
                    "bins": 10,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                }
            ],
            "storage": {
                "type": "double",
                "values": np.array(
                    [3.0, 0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 1.0]
                ),
            },
        }

    @classmethod
    @abc.abstractmethod
    def make_histogram(cls) -> T:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.h = cls.make_histogram()

    def test_access_integer(self) -> None:
        for i in range(10):
            with self.subTest(i=i):
                self.assertEqualBinValue(self.h[i], 2 * i)

        with self.assertRaises(IndexError):
            self.h[10]

        self.assertEqualBinValue(self.h[-1], 18)

    def test_access_integer_flow(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.underflow], 3)
        self.assertEqualBinValue(self.h[self.tag.overflow], 1)

    def test_access_loc(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(0.05)], 0)
        self.assertEqualBinValue(self.h[self.tag.loc(0.15)], 2)
        self.assertEqualBinValue(self.h[self.tag.loc(0.95)], 18)
        self.assertEqualBinValue(self.h[self.tag.loc(-1)], 3)
        self.assertEqualBinValue(self.h[self.tag.loc(2)], 1)

    def test_access_loc_addition(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(0.05) + 1], 2)
        self.assertEqualBinValue(self.h[self.tag.loc(0.55) + 2], 14)
        self.assertEqualBinValue(self.h[self.tag.loc(0.55) - 2], 6)

    def test_slicing_all(self) -> None:
        self.assertEqual(self.h[:], self.h)
        self.assertEqual(self.h[...], self.h)

    def test_slicing_closed(self) -> None:
        h = self.h[2:4]
        self.assertEqualBinValue(h[self.tag.underflow], 5)
        self.assertEqualBinValue(h[0], 4)
        self.assertEqualBinValue(h[1], 6)
        self.assertEqualBinValue(h[self.tag.overflow], 79)

        with self.assertRaises(IndexError):
            h[2]

    def test_slicing_open_upper(self) -> None:
        h = self.h[5:]
        self.assertEqualBinValue(h[self.tag.underflow], 23)
        self.assertEqualBinValue(h[0], 10)
        self.assertEqualBinValue(h[4], 18)
        self.assertEqualBinValue(h[self.tag.overflow], 1)
        with self.assertRaises(IndexError):
            h[5]

    def test_slicing_open_lower(self) -> None:
        h = self.h[:5]
        self.assertEqualBinValue(h[self.tag.underflow], 3)
        self.assertEqualBinValue(h[0], 0)
        self.assertEqualBinValue(h[4], 8)
        self.assertEqualBinValue(h[self.tag.overflow], 71)
        with self.assertRaises(IndexError):
            h[5]

    def test_slicing_loc_closed(self) -> None:
        h = self.h[self.tag.loc(0.2) : self.tag.loc(0.4)]
        self.assertEqualBinValue(h[self.tag.underflow], 5)
        self.assertEqualBinValue(h[0], 4)
        self.assertEqualBinValue(h[1], 6)
        self.assertEqualBinValue(h[self.tag.overflow], 79)

        with self.assertRaises(IndexError):
            h[2]

    def test_slicing_loc_open_upper(self) -> None:
        h = self.h[self.tag.loc(0.5) :]
        self.assertEqualBinValue(h[self.tag.underflow], 23)
        self.assertEqualBinValue(h[0], 10)
        self.assertEqualBinValue(h[4], 18)
        self.assertEqualBinValue(h[self.tag.overflow], 1)
        with self.assertRaises(IndexError):
            h[5]

    def test_slicing_loc_open_lower(self) -> None:
        h = self.h[: self.tag.loc(0.5)]
        self.assertEqualBinValue(h[self.tag.underflow], 3)
        self.assertEqualBinValue(h[0], 0)
        self.assertEqualBinValue(h[4], 8)
        self.assertEqualBinValue(h[self.tag.overflow], 71)
        with self.assertRaises(IndexError):
            h[5]

    def test_slicing_loc_mixed(self) -> None:
        h = self.h[2 : self.tag.loc(0.4) + 1]
        self.assertEqualBinValue(h[self.tag.underflow], 5)
        self.assertEqualBinValue(h[0], 4)
        self.assertEqualBinValue(h[1], 6)
        self.assertEqualBinValue(h[2], 8)
        self.assertEqualBinValue(h[self.tag.overflow], 71)

        with self.assertRaises(IndexError):
            h[3]

    def test_rebinning(self) -> None:
        # Boost-histogram allows the `::` to be skipped.
        h = self.h[:: self.tag.rebin(2)]
        self.assertEqualBinValue(h[0], 2)
        self.assertEqualBinValue(h[1], 10)
        self.assertEqualBinValue(h[2], 18)
        self.assertEqualBinValue(h[4], 34)

        with self.assertRaises(IndexError):
            h[5]

    def test_rebinning_with_endpoints(self) -> None:
        h = self.h[1 : 5 : self.tag.rebin(2)]
        self.assertEqualBinValue(h[0], 6)
        self.assertEqualBinValue(h[1], 14)
        with self.assertRaises(IndexError):
            h[2]

    def test_rebinning_with_endpoints_mixed(self) -> None:
        h = self.h[: self.tag.loc(0.55) : self.tag.rebin(2)]
        self.assertEqualBinValue(h[0], 2)
        self.assertEqualBinValue(h[1], 10)

        with self.assertRaises(IndexError):
            h[2]

    def test_full_integration(self) -> None:
        # boost-histogram allows the `::` to be skipped.
        v = self.h[::sum]
        self.assertEqualSum(v, 94)

    def test_non_flow_integration(self) -> None:
        v = self.h[0:len:sum]  # type: ignore[misc]
        self.assertEqualSum(v, 90)

    def test_ranged_integration(self) -> None:
        v = self.h[2:5:sum]
        self.assertEqualSum(v, 18)

    def test_open_lower_integration(self) -> None:
        v = self.h[:4:sum]
        self.assertEqualSum(v, 15)

    def test_open_upper_integration(self) -> None:
        v = self.h[4::sum]
        self.assertEqualSum(v, 79)

    def test_setting_single_value(self) -> None:
        h = self.make_histogram()
        h[0] = self.value_to_bin(42)
        self.assertEqualBinValue(h[0], 42)
        self.assertEqualBinValue(h[1], 2)
        self.assertEqualBinValue(h[-1], 18)

        h[-1] = self.value_to_bin(99)
        self.assertEqualBinValue(h[-1], 99)
        self.assertEqualBinValue(h[0], 42)
        self.assertEqualBinValue(h[1], 2)

    def test_setting_single_value_loc(self) -> None:
        h = self.make_histogram()
        h[self.tag.loc(0.05)] = self.value_to_bin(42)
        self.assertEqualBinValue(h[0], 42)
        self.assertEqualBinValue(h[1], 2)

    def test_setting_underflow(self) -> None:
        h = self.make_histogram()
        h[self.tag.underflow] = self.value_to_bin(42)
        self.assertEqualBinValue(h[self.tag.underflow], 42)
        self.assertEqualBinValue(h[0], 0)

    def test_setting_overflow(self) -> None:
        h = self.make_histogram()
        h[self.tag.overflow] = self.value_to_bin(42)
        self.assertEqualBinValue(h[self.tag.overflow], 42)
        self.assertEqualBinValue(h[-1], 18)

    def test_setting_array(self) -> None:
        h = self.make_histogram()
        h[1:3] = self.value_to_bin(42)

        # TODO: this is broken, fix!
        # self.assertEqual(h[0], 0)
        self.assertEqualBinValue(h[1], 42)
        self.assertEqualBinValue(h[2], 42)
        # self.assertEqual(h[3], 6)

    def test_setting_array_slice(self) -> None:
        h = self.make_histogram()
        h[1:3] = self.values_to_bins([42, 42])

        self.assertEqualBinValue(h[0], 0)
        self.assertEqualBinValue(h[1], 42)
        self.assertEqualBinValue(h[2], 42)
        self.assertEqualBinValue(h[3], 6)

    def test_setting_array_without_underflow(self) -> None:
        h = self.make_histogram()
        h[:3] = self.values_to_bins([42, 43, 44])
        self.assertEqualBinValue(h[self.tag.underflow], 3)
        self.assertEqualBinValue(h[0], 42)
        self.assertEqualBinValue(h[1], 43)
        self.assertEqualBinValue(h[2], 44)
        self.assertEqualBinValue(h[3], 6)

    def test_setting_array_with_underflow(self) -> None:
        h = self.make_histogram()
        h[:3] = self.values_to_bins([41, 42, 43, 44])
        self.assertEqualBinValue(h[self.tag.underflow], 41)
        self.assertEqualBinValue(h[0], 42)
        self.assertEqualBinValue(h[1], 43)
        self.assertEqualBinValue(h[2], 44)
        self.assertEqualBinValue(h[3], 6)

    def test_setting_array_without_overflow(self) -> None:
        h = self.make_histogram()
        h[7:] = self.values_to_bins([42, 43, 44])
        self.assertEqualBinValue(h[6], 12)
        self.assertEqualBinValue(h[7], 42)
        self.assertEqualBinValue(h[8], 43)
        self.assertEqualBinValue(h[9], 44)
        self.assertEqualBinValue(h[self.tag.overflow], 1)

    def test_setting_array_with_overflow(self) -> None:
        h = self.make_histogram()
        h[7:] = self.values_to_bins([42, 43, 44, 45])
        self.assertEqualBinValue(h[6], 12)
        self.assertEqualBinValue(h[7], 42)
        self.assertEqualBinValue(h[8], 43)
        self.assertEqualBinValue(h[9], 44)
        self.assertEqualBinValue(h[self.tag.overflow], 45)

    def test_setting_whole_array(self) -> None:
        h = self.make_histogram()
        h[:] = self.values_to_bins(range(10))
        self.assertEqualBinValue(h[self.tag.underflow], 3)
        self.assertEqualBinValue(h[0], 0)
        self.assertEqualBinValue(h[1], 1)
        self.assertEqualBinValue(h[2], 2)
        self.assertEqualBinValue(h[3], 3)
        self.assertEqualBinValue(h[4], 4)
        self.assertEqualBinValue(h[5], 5)
        self.assertEqualBinValue(h[6], 6)
        self.assertEqualBinValue(h[7], 7)
        self.assertEqualBinValue(h[8], 8)
        self.assertEqualBinValue(h[9], 9)
        self.assertEqualBinValue(h[self.tag.overflow], 1)

    def test_setting_whole_array_with_flow(self) -> None:
        h = self.make_histogram()
        h[:] = self.values_to_bins(range(12))
        self.assertEqualBinValue(h[self.tag.underflow], 0)
        self.assertEqualBinValue(h[0], 1)
        self.assertEqualBinValue(h[1], 2)
        self.assertEqualBinValue(h[2], 3)
        self.assertEqualBinValue(h[3], 4)
        self.assertEqualBinValue(h[4], 5)
        self.assertEqualBinValue(h[5], 6)
        self.assertEqualBinValue(h[6], 7)
        self.assertEqualBinValue(h[7], 8)
        self.assertEqualBinValue(h[8], 9)
        self.assertEqualBinValue(h[9], 10)
        self.assertEqualBinValue(h[self.tag.overflow], 11)

    def test_setting_len_mismatch(self) -> None:
        h = self.make_histogram()

        with self.assertRaises(ValueError):
            h[:] = self.values_to_bins(range(9))
        with self.assertRaises(ValueError):
            h[:] = self.values_to_bins(range(11))
        with self.assertRaises(ValueError):
            h[:] = self.values_to_bins(range(13))

        with self.assertRaises(ValueError):
            h[1:4] = self.values_to_bins(range(2))
        with self.assertRaises(ValueError):
            h[1:4] = self.values_to_bins(range(4))
        with self.assertRaises(ValueError):
            h[1:4] = self.values_to_bins(range(5))


class Indexing2D(typing.Generic[T], Indexing):
    """
    This test requires histograms to be created first.

    h is a 2D histogram with [2,5] bins. The contents are x+2y, where x and y
    are the bin indices.
    """

    h: T
    tag = uhi.tag

    @staticmethod
    def get_uhi() -> HistogramIR:
        x, y = np.mgrid[0:2, 0:5]
        data = np.pad(x + 2 * y, 1, mode="constant")
        return {
            "uhi_schema": 1,
            "axes": [
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 2.0,
                    "bins": 2,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                },
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 5.0,
                    "bins": 5,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                },
            ],
            "storage": {
                "type": "double",
                "values": data,
            },
        }

    @staticmethod
    @abc.abstractmethod
    def make_histogram() -> T:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.h = cls.make_histogram()

    def test_access_integer(self) -> None:
        for i in range(2):
            for j in range(5):
                with self.subTest(i=i, j=j):
                    self.assertEqualBinValue(self.h[i, j], i + 2 * j)

        with self.assertRaises(IndexError):
            self.h[2, 0]
        with self.assertRaises(IndexError):
            self.h[0, 5]

        self.assertEqualBinValue(self.h[-1, -1], 9)

    def test_access_loc(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), self.tag.loc(0.5)], 0)
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), self.tag.loc(1.5)], 2)
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), self.tag.loc(4.5)], 8)

    def test_access_loc_underflow(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(-1), self.tag.loc(0.5)], 0)

    def test_access_loc_mixed(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), 0], 0)
        self.assertEqualBinValue(self.h[0, self.tag.loc(1.5)], 2)
        self.assertEqualBinValue(self.h[1, self.tag.loc(4.5)], 9)

    def test_slicing_all(self) -> None:
        self.assertEqual(self.h[:, :], self.h)
        self.assertEqual(self.h[...], self.h)
        self.assertEqual(self.h[:, ...], self.h)
        self.assertEqual(self.h[..., :], self.h)

    def test_slicing_loc(self) -> None:
        h = self.h[
            1,
            self.tag.loc(0.5) : self.tag.loc(2.5),
        ]
        self.assertEqualBinValue(h[0], 1)
        self.assertEqualBinValue(h[1], 3)

        with self.assertRaises(IndexError):
            h[2]

    def test_rebinning(self) -> None:
        h = self.h[:: self.tag.rebin(2), :: self.tag.rebin(2)]
        self.assertEqualBinValue(h[0, 0], 6)
        self.assertEqualBinValue(h[0, 1], 22)

        with self.assertRaises(IndexError):
            h[0, 2]
        with self.assertRaises(IndexError):
            h[1, 0]

    def test_full_integration(self) -> None:
        v = self.h[::sum, ::sum]
        self.assertEqualSum(v, 45)

    def test_mixed_integration(self) -> None:
        h = self.h[:2:sum, 1:3]
        self.assertEqualSum(h[0], 5)
        self.assertEqualSum(h[1], 9)

        with self.assertRaises(IndexError):
            h[2]

    def test_mixed_single_integration(self) -> None:
        v = self.h[1, ::sum]
        self.assertEqualSum(v, 25)

    def test_mixed_single_integration_dict(self) -> None:
        v = self.h[{0: 1, 1: np.s_[::sum]}]
        self.assertEqualSum(v, 25)

    def test_ellipsis_integration(self) -> None:
        h = self.h[..., ::sum]
        self.assertEqualSum(h[0], 20)
        self.assertEqualSum(h[1], 25)

        with self.assertRaises(IndexError):
            h[2]

    def test_ellipsis_integration_dict(self) -> None:
        h = self.h[{0: np.s_[::sum]}]
        self.assertEqualSum(h[0], 1)
        self.assertEqualSum(h[1], 5)
        self.assertEqualSum(h[4], 17)

        with self.assertRaises(IndexError):
            h[5]

    def test_setting_single_value(self) -> None:
        h = self.make_histogram()
        h[0, 0] = self.value_to_bin(42)
        self.assertEqualBinValue(h[0, 0], 42)
        self.assertEqualBinValue(h[1, 1], 3)

    def test_setting_underflow(self) -> None:
        h = self.make_histogram()
        h[self.tag.underflow, ...] = self.value_to_bin(42)
        self.assertEqualBinValue(h[self.tag.underflow, 0], 42)

    def test_setting_array(self) -> None:
        h = self.make_histogram()

        h[0:2, 0:2] = np.array(
            [self.values_to_bins([42, 43]), self.values_to_bins([44, 45])]
        )
        self.assertEqualBinValue(h[0, 0], 42)
        self.assertEqualBinValue(h[0, 1], 43)
        self.assertEqualBinValue(h[1, 0], 44)
        self.assertEqualBinValue(h[1, 1], 45)
        self.assertEqualBinValue(h[1, 2], 5)

    def test_setting_array_broadcast(self) -> None:
        h = self.make_histogram()

        h[0:2, 0:2] = np.array([self.values_to_bins([42]), self.values_to_bins([3])])
        self.assertEqualBinValue(h[0, 0], 42)
        self.assertEqualBinValue(h[0, 1], 42)
        self.assertEqualBinValue(h[1, 0], 3)
        self.assertEqualBinValue(h[1, 1], 3)
        self.assertEqualBinValue(h[1, 2], 5)

    def test_setting_dict(self) -> None:
        h = self.make_histogram()
        h[{0: 1, 1: 0}] = self.value_to_bin(42)
        self.assertEqualBinValue(h[1, 0], 42)
        self.assertEqualBinValue(h[0, 1], 2)

    def test_setting_dict_slice(self) -> None:
        h = self.make_histogram()

        h[{0: 1, 1: slice(2, 4)}] = self.values_to_bins(range(42, 44))

        self.assertEqualBinValue(h[1, 1], 3)
        self.assertEqualBinValue(h[1, 2], 42)
        self.assertEqualBinValue(h[1, 3], 43)
        self.assertEqualBinValue(h[1, 4], 9)

    def test_setting_dict_slicer(self) -> None:
        h = self.make_histogram()

        h[{0: 1, 1: np.s_[3:5]}] = self.values_to_bins(range(42, 44))
        self.assertEqualBinValue(h[1, 2], 5)
        self.assertEqualBinValue(h[1, 3], 42)
        self.assertEqualBinValue(h[1, 4], 43)


class Indexing3D(typing.Generic[T], Indexing):
    """
    This test requires histograms to be created first.

    h is a 3D histogram with [2,5,10] bins. The contents are x+2y+3z, where x,
    y, and z are the bin indices.
    """

    h: T
    tag = uhi.tag

    @staticmethod
    def get_uhi() -> HistogramIR:
        x, y, z = np.mgrid[0:2, 0:5, 0:10]
        data = np.pad(x + 2 * y + 3 * z, 1, mode="constant")
        return {
            "uhi_schema": 1,
            "writer_info": {"boost-histogram": {"version": "1.6.1"}},
            "axes": [
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 2.0,
                    "bins": 2,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                    "metadata": {},
                },
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 5.0,
                    "bins": 5,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                    "metadata": {},
                },
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 10.0,
                    "bins": 10,
                    "underflow": True,
                    "overflow": True,
                    "circular": False,
                    "metadata": {},
                },
            ],
            "storage": {
                "type": "double",
                "values": data,
            },
            "metadata": {"_variance_known": True},
        }

    @classmethod
    @abc.abstractmethod
    def make_histogram(cls) -> T:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.h = cls.make_histogram()

    def test_access_integer(self) -> None:
        for i in range(2):
            for j in range(5):
                for k in range(10):
                    with self.subTest(i=i, j=j, k=k):
                        self.assertEqualBinValue(self.h[i, j, k], i + 2 * j + 3 * k)

        with self.assertRaises(IndexError):
            self.h[2, 0, 0]
        with self.assertRaises(IndexError):
            self.h[0, 5, 0]
        with self.assertRaises(IndexError):
            self.h[0, 0, 10]

        self.assertEqualBinValue(self.h[-1, -1, -1], 36)

    def test_access_loc(self) -> None:
        self.assertEqualBinValue(
            self.h[self.tag.loc(0.5), self.tag.loc(0.5), self.tag.loc(0.5)], 0
        )
        self.assertEqualBinValue(
            self.h[self.tag.loc(0.5), self.tag.loc(1.5), self.tag.loc(0.5)], 2
        )
        self.assertEqualBinValue(
            self.h[self.tag.loc(0.5), self.tag.loc(4.5), self.tag.loc(9.5)], 35
        )
        self.assertEqualBinValue(
            self.h[self.tag.loc(-1), self.tag.loc(0.5), self.tag.loc(0.5)], 0
        )

    def test_access_loc_mixed(self) -> None:
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), 0, self.tag.loc(0.5)], 0)
        self.assertEqualBinValue(self.h[0, self.tag.loc(1.5), self.tag.loc(0.5)], 2)
        self.assertEqualBinValue(self.h[self.tag.loc(0.5), self.tag.loc(4.5), 9], 35)
        self.assertEqualBinValue(self.h[1, self.tag.loc(4.5), 9], 36)

    def test_slicing_all(self) -> None:
        self.assertEqual(self.h[:, :, :], self.h)
        self.assertEqual(self.h[...], self.h)
        self.assertEqual(self.h[:, ...], self.h)
        self.assertEqual(self.h[..., :], self.h)

    def test_slicing_loc(self) -> None:
        h = self.h[
            1,
            3,
            self.tag.loc(0.5) : self.tag.loc(2.5),
        ]
        self.assertEqualBinValue(h[0], 7)
        self.assertEqualBinValue(h[1], 10)

        with self.assertRaises(IndexError):
            h[2]

    def test_rebinning(self) -> None:
        h = self.h[:: self.tag.rebin(2), :: self.tag.rebin(2), :: self.tag.rebin(2)]
        self.assertEqualBinValue(h[0, 0, 0], 24)
        self.assertEqualBinValue(h[0, 0, 1], 72)
        self.assertEqualBinValue(h[0, 1, 0], 56)
        self.assertEqualBinValue(h[0, 1, 4], 248)

        with self.assertRaises(IndexError):
            h[0, 1, 5]
        with self.assertRaises(IndexError):
            h[0, 2, 4]
        with self.assertRaises(IndexError):
            h[1, 1, 4]

    def test_full_integration(self) -> None:
        v = self.h[::sum, ::sum, ::sum]
        self.assertEqualSum(v, 1800)

    def test_mixed_integration(self) -> None:
        h = self.h[::sum, :2:sum, 1:3]
        self.assertEqualSum(h[0], 18)
        self.assertEqualSum(h[1], 30)

        with self.assertRaises(IndexError):
            h[2]

    def test_mixed_single_integration(self) -> None:
        h = self.h[1, ::sum, 1:3]
        self.assertEqualSum(h[0], 40)
        self.assertEqualSum(h[1], 55)

        with self.assertRaises(IndexError):
            h[2]

    def test_mixed_single_integration_dict(self) -> None:
        h = self.h[{0: 1, 1: np.s_[::sum], 2: np.s_[1:3]}]
        self.assertEqualSum(h[0], 40)
        self.assertEqualSum(h[1], 55)

        with self.assertRaises(IndexError):
            h[2]

    def test_ellipsis_integration(self) -> None:
        h = self.h[::sum, ..., ::sum]
        self.assertEqualSum(h[0], 280)
        self.assertEqualSum(h[1], 320)
        self.assertEqualSum(h[4], 440)

        with self.assertRaises(IndexError):
            h[5]

    def test_ellipsis_integration_dict(self) -> None:
        h = self.h[{0: np.s_[::sum], 2: np.s_[::sum]}]
        self.assertEqualSum(h[0], 280)
        self.assertEqualSum(h[1], 320)
        self.assertEqualSum(h[4], 440)

        with self.assertRaises(IndexError):
            h[5]

    def test_setting_single_value(self) -> None:
        h = self.make_histogram()
        h[0, 0, 0] = 42
        self.assertEqualBinValue(h[0, 0, 0], 42)
        self.assertEqualBinValue(h[1, 1, 1], 6)

    def test_setting_underflow(self) -> None:
        h = self.make_histogram()
        h[self.tag.underflow, ...] = 42
        self.assertEqualBinValue(h[self.tag.underflow, 0, 0], 42)

    def test_setting_array(self) -> None:
        h = self.make_histogram()

        h[0:2, 0:2, 0:2] = np.array(
            [
                [self.values_to_bins([42, 43]), self.values_to_bins([44, 45])],
                [self.values_to_bins([46, 47]), self.values_to_bins([48, 49])],
            ]
        )
        self.assertEqualBinValue(h[0, 0, 0], 42)
        self.assertEqualBinValue(h[0, 0, 1], 43)
        self.assertEqualBinValue(h[0, 1, 0], 44)
        self.assertEqualBinValue(h[0, 1, 1], 45)
        self.assertEqualBinValue(h[1, 0, 0], 46)
        self.assertEqualBinValue(h[1, 0, 1], 47)
        self.assertEqualBinValue(h[1, 1, 0], 48)
        self.assertEqualBinValue(h[1, 1, 1], 49)
        self.assertEqualBinValue(h[1, 1, 2], 9)

    def test_setting_array_broadcast(self) -> None:
        h = self.make_histogram()

        h[0:2, 0:2, 0:2] = np.array(
            [
                [self.values_to_bins([42]), self.values_to_bins([3])],
                [self.values_to_bins([46]), self.values_to_bins([4])],
            ]
        )
        self.assertEqualBinValue(h[0, 0, 0], 42)
        self.assertEqualBinValue(h[0, 0, 1], 42)
        self.assertEqualBinValue(h[0, 1, 0], 3)
        self.assertEqualBinValue(h[0, 1, 1], 3)
        self.assertEqualBinValue(h[1, 0, 0], 46)
        self.assertEqualBinValue(h[1, 0, 1], 46)
        self.assertEqualBinValue(h[1, 1, 0], 4)
        self.assertEqualBinValue(h[1, 1, 1], 4)
        self.assertEqualBinValue(h[1, 1, 2], 9)

    def test_setting_dict(self) -> None:
        h = self.make_histogram()
        h[{0: 1, 1: 0, 2: 3}] = self.value_to_bin(3)
        self.assertEqualBinValue(h[1, 0, 3], 3)
        self.assertEqualBinValue(h[1, 0, 4], 13)

    def test_setting_dict_slice(self) -> None:
        h = self.make_histogram()

        h[{0: 1, 1: 0, 2: slice(3, 5)}] = self.values_to_bins(range(42, 44))

        self.assertEqualBinValue(h[1, 0, 2], 7)
        self.assertEqualBinValue(h[1, 0, 3], 42)
        self.assertEqualBinValue(h[1, 0, 4], 43)
        self.assertEqualBinValue(h[1, 0, 5], 16)

    def test_setting_dict_slicer(self) -> None:
        h = self.make_histogram()

        h[{0: 1, 1: 0, 2: np.s_[3:5]}] = self.values_to_bins(range(42, 44))
        self.assertEqualBinValue(h[1, 0, 2], 7)
        self.assertEqualBinValue(h[1, 0, 3], 42)
        self.assertEqualBinValue(h[1, 0, 4], 43)
        self.assertEqualBinValue(h[1, 0, 5], 16)
