from __future__ import annotations

from typing import Any

import awkward as ak
import numpy as np
import uproot

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram
from ._rntuple import from_fields, to_fields

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(
    directory: uproot.WritableDirectory,
    /,
    name: str,
    histogram: AnyHistogramIR | ToUHIHistogram,
) -> None:
    """
    Write a histogram to an uproot directory as a single-entry RNTuple, in
    the same layout as :func:`uhi.io.root.write`.
    """
    uhi, arrays = to_fields(histogram)
    data = {"uhi": ak.Array([uhi])}
    for field, array in arrays.items():
        data[field] = ak.unflatten(array, [len(array)])
    directory.mkrntuple(name, data)


def read(directory: uproot.ReadOnlyDirectory, /, name: str) -> dict[str, Any]:
    """
    Read a histogram from an uproot directory.
    """
    entry = directory[name].arrays()[0]
    return from_fields(entry["uhi"], lambda field: np.asarray(entry[field]))
