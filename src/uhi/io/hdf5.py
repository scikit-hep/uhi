from __future__ import annotations

from typing import Any

import h5py
import numpy as np

from ..typing.serialization import AnyAxis, AnyHistogram, AnyStorage, Histogram
from . import ARRAY_KEYS

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def write(grp: h5py.Group, /, histogram: AnyHistogram) -> None:
    """
    Write a histogram to an HDF5 group.
    """
    # All referenced objects will be stored inside of /{name}/ref_axes
    hist_folder_storage = grp.create_group("ref_axes")

    # Metadata

    if "metadata" in histogram:
        metadata_grp = grp.create_group("metadata")
        for key, val1 in histogram["metadata"].items():
            metadata_grp.attrs[key] = val1

    # Axes
    axes_dataset = grp.create_dataset(
        "axes", len(histogram["axes"]), dtype=h5py.special_dtype(ref=h5py.Reference)
    )
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
            ax_group.create_dataset("edges", shape=ax_edges.shape, data=ax_edges)
        if ax_cats is not None:
            ax_group.create_dataset("categories", shape=len(ax_cats), data=ax_cats)
        axes_dataset[i] = ax_group.ref

    # Storage
    storage_grp = grp.create_group("storage")
    storage_type = histogram["storage"]["type"]

    storage_grp.attrs["type"] = storage_type

    for key, val3 in histogram["storage"].items():
        if key == "type":
            continue
        npvalue = np.asarray(val3)
        storage_grp.create_dataset(key, shape=npvalue.shape, data=npvalue)


def _convert_axes(group: h5py.Group | h5py.Dataset | h5py.Datatype) -> AnyAxis:
    """
    Convert an HDF5 axis reference to a dictionary.
    """
    assert isinstance(group, h5py.Group)

    axis = {k: _convert_item(k, v) for k, v in group.attrs.items()}
    if "edges" in group:
        edges = group["edges"]
        assert isinstance(edges, h5py.Dataset)
        axis["edges"] = np.asarray(edges)
    if "categories" in group:
        categories = group["categories"]
        assert isinstance(categories, h5py.Dataset)
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


def read(grp: h5py.Group, /) -> Histogram:
    """
    Read a histogram from an HDF5 group.
    """
    axes_grp = grp["axes"]
    axes_ref = grp["ref_axes"]
    assert isinstance(axes_ref, h5py.Group)
    assert isinstance(axes_grp, h5py.Dataset)

    axes = [_convert_axes(axes_ref[unref_axis_ref]) for unref_axis_ref in axes_ref]

    storage_grp = grp["storage"]
    assert isinstance(storage_grp, h5py.Group)
    storage = AnyStorage(type=storage_grp.attrs["type"])
    for key in storage_grp:
        storage[key] = np.asarray(storage_grp[key])  # type: ignore[literal-required]

    histogram_dict = AnyHistogram(axes=axes, storage=storage)
    if "metadata" in grp:
        histogram_dict["metadata"] = _convert_item("metadata", grp["metadata"].attrs)

    return histogram_dict  # type: ignore[return-value]
