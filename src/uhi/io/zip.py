from __future__ import annotations

import json
import zipfile
from typing import Any

import numpy as np

from ..typing.serialization import AnyHistogram, Histogram
from . import ARRAY_KEYS

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(
    zip_file: zipfile.ZipFile,
    /,
    name: str,
    histogram: AnyHistogram,
) -> None:
    """
    Write a histogram to a zip file.
    """
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


def read(zip_file: zipfile.ZipFile, /, name: str) -> Histogram:
    """
    Read histograms from a zip file.
    """

    def object_hook(dct: dict[str, Any], /) -> dict[str, Any]:
        for item in ARRAY_KEYS & dct.keys():
            if isinstance(dct[item], str):
                dct[item] = np.load(zip_file.open(dct[item]))
        return dct

    with zip_file.open(f"{name}.json") as f:
        return json.load(f, object_hook=object_hook)  # type: ignore[no-any-return]
