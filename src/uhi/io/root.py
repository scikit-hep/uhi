from __future__ import annotations

from typing import Any

import numpy as np
import ROOT

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram
from ._rntuple import FIELD_TYPES, from_fields, to_fields

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(
    directory: ROOT.TDirectory,
    /,
    name: str,
    histogram: AnyHistogramIR | ToUHIHistogram,
) -> None:
    """
    Write a histogram to a ROOT directory as a single-entry RNTuple. The
    histogram JSON is stored in the ``uhi`` field; each array is stored
    flattened in a vector field of the same name.
    """
    uhi, arrays = to_fields(histogram)

    model = ROOT.RNTupleModel.Create()
    model.MakeField["std::string"]("uhi")
    vectors = {}
    for field, array in arrays.items():
        ctype = FIELD_TYPES[array.dtype.name]
        model.MakeField[f"std::vector<{ctype}>"](field)
        vectors[field] = ROOT.std.vector[ctype](array)

    with ROOT.RNTupleWriter.Append(model, name, directory) as writer:
        entry = writer.CreateEntry()
        entry["uhi"] = uhi
        for field, vector in vectors.items():
            entry[field] = ROOT.std.move(vector)
        writer.Fill(entry)


def read(directory: ROOT.TDirectory, /, name: str) -> dict[str, Any]:
    """
    Read a histogram from a ROOT directory.
    """
    with ROOT.RNTupleReader.Open(directory.Get(name)) as reader:
        entry = reader.CreateEntry()
        reader.LoadEntry(0, entry)
        return from_fields(str(entry["uhi"]), lambda field: np.array(entry[field]))
