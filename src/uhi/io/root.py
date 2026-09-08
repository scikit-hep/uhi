from __future__ import annotations

import json
from typing import Any

import numpy as np
import ROOT

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram
from . import ARRAY_KEYS, _compute_axis_length
from ._common import _check_uhi_schema_version, _convert_input

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


_FIELD_TYPES = {
    "float64": "double",
    "float32": "float",
    "int64": "std::int64_t",
    "int32": "std::int32_t",
    "uint64": "std::uint64_t",
    "uint32": "std::uint32_t",
}


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

    model = ROOT.RNTupleModel.Create()
    model.MakeField["std::string"]("uhi")
    vectors = {}
    for field, array in arrays.items():
        ctype = _FIELD_TYPES.get(array.dtype.name)
        if ctype is None:
            msg = f"Unsupported array dtype {array.dtype} for {field}"
            raise TypeError(msg)
        model.MakeField[f"std::vector<{ctype}>"](field)
        vectors[field] = ROOT.std.vector[ctype](array.ravel())

    with ROOT.RNTupleWriter.Append(model, name, directory) as writer:
        entry = writer.CreateEntry()
        entry["uhi"] = json.dumps(histogram)
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
        output: dict[str, Any] = json.loads(str(entry["uhi"]))
        # Only storage and axes contain array references; metadata and writer
        # info may use the same keys for arbitrary strings.
        for obj in [output["storage"], *output["axes"]]:
            for key in ARRAY_KEYS & obj.keys():
                if isinstance(obj[key], str):
                    obj[key] = np.array(entry[obj[key]])
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
