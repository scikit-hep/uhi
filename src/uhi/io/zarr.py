from __future__ import annotations

from typing import Any

import numpy as np
import zarr

from ..typing.serialization import AnyAxis, AnyHistogram, AnyStorage, Histogram
from . import ARRAY_KEYS

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(grp: zarr.Group, /, histogram: AnyHistogram) -> None:
    """
    Write a histogram to a Zarr group.
    """
    # All referenced objects will be stored inside of /{name}/axes
    hist_folder_storage = grp.create_group("axes")

    # Metadata

    if "metadata" in histogram:
        metadata_grp = grp.create_group("metadata")
        for key, val1 in histogram["metadata"].items():
            metadata_grp.attrs[key] = val1

    # Axes
    for i, axis in enumerate(histogram["axes"]):
        # Iterating through the axes, calling `create_axes_object` for each of them,
        # creating references to new groups and appending it to the `items` dataset defined above
        ax_group = hist_folder_storage.create_group(f"axis_{i}")
        ax_info = axis.copy()
        ax_metadata = ax_info.pop("metadata", None)
        ax_edges_raw = ax_info.pop("edges", None)
        ax_edges = np.asarray(ax_edges_raw) if ax_edges_raw is not None else None
        ax_cats: list[int] | list[str] | None = ax_info.pop("categories", None)
        for key, val2 in ax_info.items():
            ax_group.attrs[key] = val2
        if ax_metadata is not None:
            ax_metadata_grp = ax_group.create_group("metadata")
            for k, v in ax_metadata.items():
                ax_metadata_grp.attrs[k] = v
        if ax_edges is not None:
            arr = ax_group.create_array(
                "edges", shape=ax_edges.shape, dtype=ax_edges.dtype
            )
            arr[:] = ax_edges
        if ax_cats is not None:
            # zarr v3 doesn't support str dtype yet, so we attach it to attrs (which should be ok in general)
            ax_group.attrs["categories"] = ax_cats

    # Storage
    storage_grp = grp.create_group("storage")
    storage_type = histogram["storage"]["type"]

    storage_grp.attrs["type"] = storage_type

    for key, val3 in histogram["storage"].items():
        if key == "type":
            continue
        npvalue = np.asarray(val3)
        arr = storage_grp.create_array(key, shape=npvalue.shape, dtype=npvalue.dtype)
        arr[:] = npvalue


def _convert_axes(group: zarr.Group | zarr.Dataset | zarr.Datatype) -> AnyAxis:
    """
    Convert a Zarr axis reference to a dictionary.
    """
    axis = {k: _convert_item(k, v) for k, v in group.attrs.items()}
    if "edges" in group:
        edges = group["edges"]
        assert isinstance(edges, zarr.Array)
        axis["edges"] = np.asarray(edges)
    if "categories" in group.attrs:
        categories = group.attrs["categories"]
        axis["categories"] = [_convert_item("", c) for c in categories]

    return axis  # type: ignore[return-value]


def _convert_item(name: str, item: Any, /) -> Any:
    """
    Convert an HDF5 item to a native Python type.
    """
    if isinstance(item, bytes):
        return item.decode("utf-8")
    if name == "metadata":
        return {k: _convert_item("", v) for k, v in item.items()}
    if name in ARRAY_KEYS:
        return item
    if isinstance(item, np.generic):
        return item.item()
    return item


def read(grp: zarr.Group, /) -> Histogram:
    """
    Read a histogram from a Zarr group.
    """
    axes_grp = grp["axes"]
    assert isinstance(axes_grp, zarr.Group)

    axes = [_convert_axes(axes_grp[ax]) for ax in sorted(axes_grp)]

    storage_grp = grp["storage"]
    assert isinstance(storage_grp, zarr.Group)
    storage = AnyStorage(type=storage_grp.attrs["type"])
    for key in storage_grp:
        storage[key] = np.asarray(storage_grp[key])  # type: ignore[literal-required]

    histogram_dict = AnyHistogram(axes=axes, storage=storage)
    if "metadata" in grp:
        histogram_dict["metadata"] = _convert_item("metadata", grp["metadata"].attrs)

    return histogram_dict  # type: ignore[return-value]
