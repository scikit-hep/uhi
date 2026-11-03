from __future__ import annotations

import typing
from typing import Any

import numpy as np
import zarr

from ..typing.serialization import (
    AnyAxisIR,
    AnyHistogramIR,
    AnyStorageIR,
    HistogramIR,
    ToUHIHistogram,
)
from ._common import _check_uhi_schema_version, _convert_input

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def _create_array(group: zarr.Group, name: str, data: Any) -> None:
    """
    Create an array stored as a single chunk, so the layout on disk only
    depends on the data. Strings use the variable-length UTF-8 type.
    """
    arr = np.asarray(data)
    if arr.dtype.kind == "U":
        arr = arr.astype(np.dtypes.StringDType())
    # Zarr does not allow zero-length chunks
    chunks = tuple(max(s, 1) for s in arr.shape)
    group.create_array(name, data=arr, chunks=chunks)


def write(grp: zarr.Group, /, histogram: AnyHistogramIR | ToUHIHistogram) -> None:
    """
    Write a histogram to a Zarr group. Each array is one chunk.
    """
    histogram = _convert_input(histogram)

    # Zarr attributes are JSON, so metadata and writer_info are stored as-is
    grp.attrs["uhi_schema"] = histogram["uhi_schema"]
    if "metadata" in histogram:
        grp.attrs["metadata"] = histogram["metadata"]
    if "writer_info" in histogram:
        grp.attrs["writer_info"] = histogram["writer_info"]

    # Axes
    axes_grp = grp.create_group("axes")
    for i, axis in enumerate(histogram["axes"]):
        ax_group = axes_grp.create_group(f"axis_{i}")
        ax_info = dict(axis)
        ax_edges = ax_info.pop("edges", None)
        ax_cats = ax_info.pop("categories", None)
        ax_group.attrs.update(ax_info)  # type: ignore[arg-type]
        if ax_edges is not None:
            _create_array(ax_group, "edges", ax_edges)
        if ax_cats is not None:
            _create_array(ax_group, "categories", ax_cats)

    # Storage
    storage_grp = grp.create_group("storage")
    storage_grp.attrs["type"] = histogram["storage"]["type"]
    for key, value in histogram["storage"].items():
        if key != "type":
            _create_array(storage_grp, key, value)


def _convert_axis(group: zarr.Group) -> AnyAxisIR:
    """
    Convert a Zarr axis group to a dictionary.
    """
    axis = typing.cast(AnyAxisIR, dict(group.attrs))
    if "edges" in group:
        axis["edges"] = np.asarray(group["edges"])
    if "categories" in group:
        axis["categories"] = np.asarray(group["categories"]).tolist()
    return axis


def read(grp: zarr.Group, /) -> HistogramIR:
    """
    Read a histogram from a Zarr group.
    """
    uhi_schema = grp.attrs["uhi_schema"]
    assert isinstance(uhi_schema, int)
    _check_uhi_schema_version(uhi_schema)

    axes_grp = grp["axes"]
    assert isinstance(axes_grp, zarr.Group)
    # Group members are not ordered, so look up each axis by index
    axes = [
        _convert_axis(typing.cast(zarr.Group, axes_grp[f"axis_{i}"]))
        for i in range(len(axes_grp))
    ]

    storage_grp = grp["storage"]
    assert isinstance(storage_grp, zarr.Group)
    storage = AnyStorageIR(type=storage_grp.attrs["type"])  # type: ignore[typeddict-item]
    for key in storage_grp:
        storage[key] = np.asarray(storage_grp[key])  # type: ignore[literal-required]

    histogram_dict = AnyHistogramIR(uhi_schema=uhi_schema, axes=axes, storage=storage)
    if "metadata" in grp.attrs:
        histogram_dict["metadata"] = grp.attrs["metadata"]  # type: ignore[typeddict-item]
    if "writer_info" in grp.attrs:
        histogram_dict["writer_info"] = grp.attrs["writer_info"]  # type: ignore[typeddict-item]

    return histogram_dict  # type: ignore[return-value]
