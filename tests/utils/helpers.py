"""Helper functions for histogram testing."""

from __future__ import annotations

import sys
import typing
from collections.abc import Mapping
from typing import Any

import numpy as np

if sys.version_info < (3, 11):
    from typing import TypeAlias
else:
    from typing import TypeAlias

from uhi.typing.serialization import AnyHistogramIR, AnyStorageIR

__all__ = ["convert_histogram_to_32bit"]

# Type alias for arrays that can be converted
ArrayLike: TypeAlias = (
    np.ndarray | list[typing.Any] | int | np.integer | float | np.floating | None
)


def _convert_array_to_32bit(arr: ArrayLike) -> ArrayLike:
    """Recursively convert numeric arrays to 32-bit precision.

    Uses pattern matching to handle different array types.
    """
    match arr:
        case np.ndarray():
            if np.issubdtype(arr.dtype, np.floating):
                return arr.astype(np.float32)
            if np.issubdtype(arr.dtype, np.signedinteger):
                return arr.astype(np.int32)
            if np.issubdtype(arr.dtype, np.unsignedinteger):
                return arr.astype(np.uint32)
            return arr
        case list():
            return [_convert_array_to_32bit(item) for item in arr]
        case int(n) if n > 2147483647 or n < -2147483648:
            return np.int32(n)
        case _ as other:
            return other


def convert_histogram_to_32bit(hist: Mapping[str, Any]) -> AnyHistogramIR:
    """Convert a histogram dictionary to use 32-bit values where applicable.

    This processes the storage arrays and converts float64 to float32 and
    int64 to int32 (where appropriate).

    Args:
        hist: A histogram in UHI format

    Returns:
        A histogram with 32-bit precision storage arrays
    """
    hist_copy: AnyHistogramIR = typing.cast(AnyHistogramIR, {**hist})

    if "storage" in hist_copy:
        storage: AnyStorageIR = typing.cast(AnyStorageIR, {**hist_copy["storage"]})
        storage_type = storage.get("type")

        match storage_type:
            case "int":
                # Convert integer values to int32
                if "values" in storage:
                    storage["values"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["values"])
                    )
                if "index" in storage:
                    storage["index"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["index"])
                    )

            case "double":
                # Convert float values to float32
                if "values" in storage:
                    storage["values"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["values"])
                    )
                if "index" in storage:
                    storage["index"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["index"])
                    )

            case "weighted":
                # Convert float values and variances to float32
                if "values" in storage:
                    storage["values"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["values"])
                    )
                if "variances" in storage:
                    storage["variances"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["variances"])
                    )
                if "index" in storage:
                    storage["index"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["index"])
                    )

            case "mean":
                # Convert counts, values, and variances to float32
                if "counts" in storage:
                    storage["counts"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["counts"])
                    )
                if "values" in storage:
                    storage["values"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["values"])
                    )
                if "variances" in storage:
                    storage["variances"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["variances"])
                    )
                if "index" in storage:
                    storage["index"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["index"])
                    )

            case "weighted_mean":
                # Convert all float arrays to float32
                if "sum_of_weights" in storage:
                    storage["sum_of_weights"] = typing.cast(
                        np.ndarray,
                        _convert_array_to_32bit(storage["sum_of_weights"]),
                    )
                if "sum_of_weights_squared" in storage:
                    storage["sum_of_weights_squared"] = typing.cast(
                        np.ndarray,
                        _convert_array_to_32bit(storage["sum_of_weights_squared"]),
                    )
                if "values" in storage:
                    storage["values"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["values"])
                    )
                if "variances" in storage:
                    storage["variances"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["variances"])
                    )
                if "index" in storage:
                    storage["index"] = typing.cast(
                        np.ndarray, _convert_array_to_32bit(storage["index"])
                    )

        hist_copy["storage"] = storage

    return hist_copy
