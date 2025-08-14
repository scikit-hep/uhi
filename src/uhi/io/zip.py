from __future__ import annotations

import functools
import json
import zipfile
from typing import Any

import numpy as np

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram
from . import ARRAY_KEYS
from ._common import _check_uhi_schema_version, _convert_input

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(
    zip_file: zipfile.ZipFile,
    /,
    name: str,
    histogram: AnyHistogramIR | ToUHIHistogram,
) -> None:
    """
    Write a histogram to a zip file.
    """
    histogram = _convert_input(histogram)
    # Write out numpy arrays to files in the zipfile
    for storage_key in ARRAY_KEYS & histogram["storage"].keys():
        path = f"{name}_storage_{storage_key}.npy"
        with zip_file.open(path, "w") as f:
            np.save(f, histogram["storage"][storage_key])  # type: ignore[literal-required]
        histogram["storage"][storage_key] = path  # type: ignore[literal-required]

    for axis in histogram["axes"]:
        for key in ARRAY_KEYS & axis.keys():
            path = f"{name}_axis_{key}.npy"
            with zip_file.open(path, "w") as f:
                np.save(f, axis[key])  # type: ignore[literal-required]
            axis[key] = path  # type: ignore[literal-required]

    hist_json = json.dumps(histogram)
    zip_file.writestr(f"{name}.json", hist_json)


def _object_hook(
    dct: dict[str, Any], /, *, zip_file: zipfile.ZipFile
) -> dict[str, Any]:
    for item in ARRAY_KEYS & dct.keys():
        if isinstance(dct[item], str):
            dct[item] = np.load(zip_file.open(dct[item]))
    return dct


def read(zip_file: zipfile.ZipFile, /, name: str) -> dict[str, Any]:
    """
    Read histograms from a zip file.
    """

    object_hook = functools.partial(_object_hook, zip_file=zip_file)
    with zip_file.open(f"{name}.json") as f:
        output: dict[str, Any] = json.load(f, object_hook=object_hook)
        _check_uhi_schema_version(output["uhi_schema"])
        return output
