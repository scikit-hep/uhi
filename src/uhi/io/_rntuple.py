"""
Shared layout for the RNTuple format, used by both the ROOT and uproot
backends. A histogram is one entry: a ``uhi`` string field holds the IR as
JSON, with each array replaced by the name of the vector field holding it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram
from . import ARRAY_KEYS, _compute_axis_length
from ._common import _check_uhi_schema_version, _convert_input

__all__ = ["FIELD_TYPES", "from_fields", "to_fields"]


def __dir__() -> list[str]:
    return __all__


# Supported array dtypes and their C++ RNTuple field types
FIELD_TYPES = {
    "float64": "double",
    "float32": "float",
    "int64": "std::int64_t",
    "int32": "std::int32_t",
    "uint64": "std::uint64_t",
    "uint32": "std::uint32_t",
}


def to_fields(
    histogram: AnyHistogramIR | ToUHIHistogram, /
) -> tuple[str, dict[str, np.ndarray[Any, Any]]]:
    """
    Split a histogram into the ``uhi`` JSON string and a dict of flat arrays.
    """
    histogram = _convert_input(histogram)
    # Copy the histogram and the dicts/lists we mutate below so the caller's
    # arrays are not replaced with field names.
    histogram = histogram.copy()

    arrays: dict[str, np.ndarray[Any, Any]] = {}
    storage = histogram["storage"].copy()
    histogram["storage"] = storage
    for storage_key in ARRAY_KEYS & storage.keys():
        arrays[storage_key] = np.asarray(storage[storage_key])  # type: ignore[literal-required]
        storage[storage_key] = storage_key  # type: ignore[literal-required]

    axes = [axis.copy() for axis in histogram["axes"]]
    histogram["axes"] = axes
    for i, axis in enumerate(axes):
        for key in ARRAY_KEYS & axis.keys():
            field = f"axis_{i}_{key}"
            arrays[field] = np.asarray(axis[key])  # type: ignore[literal-required]
            axis[key] = field  # type: ignore[literal-required]

    for field, array in arrays.items():
        if array.dtype.name not in FIELD_TYPES:
            msg = f"Unsupported array dtype {array.dtype} for {field}"
            raise TypeError(msg)
        # Awkward and RNTuple need native byte order
        arrays[field] = array.astype(array.dtype.newbyteorder("="), copy=False).ravel()

    return json.dumps(histogram), arrays


def from_fields(
    uhi: str, get_array: Callable[[str], np.ndarray[Any, Any]], /
) -> dict[str, Any]:
    """
    Rebuild a histogram from the ``uhi`` JSON string, reading each array field
    with ``get_array``.
    """
    output: dict[str, Any] = json.loads(uhi)
    # Only storage and axes contain array references; metadata and writer
    # info may use the same keys for arbitrary strings.
    for obj in [output["storage"], *output["axes"]]:
        for key in ARRAY_KEYS & obj.keys():
            if isinstance(obj[key], str):
                obj[key] = get_array(obj[key])
    _check_uhi_schema_version(output["uhi_schema"])

    # Arrays are stored flattened; the shape is recovered from the axes
    storage = output["storage"]
    if "index" in storage:
        storage["index"] = storage["index"].reshape(len(output["axes"]), -1)
    elif output["axes"]:
        shape = [_compute_axis_length(axis) for axis in output["axes"]]
        for key in ARRAY_KEYS & storage.keys():
            storage[key] = storage[key].reshape(shape)
    return output
