from __future__ import annotations

import typing
from typing import Any

import h5py
import numpy as np

from ..typing.serialization import (
    AnyAxisIR,
    AnyHistogramIR,
    AnyStorageIR,
    HistogramIR,
    SupportedMetadata,
    ToUHIHistogram,
)
from . import ARRAY_KEYS
from ._common import _check_uhi_schema_version, _convert_input

__all__ = ["read", "write"]


def __dir__() -> list[str]:
    return __all__


def _handle_metadata_writer_info(
    grp: h5py.Group,
    metadata: dict[str, SupportedMetadata] | None,
    writer_info: dict[str, dict[str, SupportedMetadata]] | None,
) -> None:
    # Metadata
    if metadata:
        metadata_grp = grp.create_group("metadata")
        for key, val1 in metadata.items():
            metadata_grp.attrs[key] = val1

    # Writer info
    if writer_info:
        writer_info_grp = grp.create_group("writer_info")
        for key, value in writer_info.items():
            inner_wi_grp = writer_info_grp.create_group(key)
            for k, v in value.items():
                inner_wi_grp.attrs[k] = v


def write(
    grp: h5py.Group,
    /,
    histogram: AnyHistogramIR | ToUHIHistogram,
    *,
    compression: str = "gzip",
    compression_opts: int = 4,
    min_compress_elements: int = 1_000,
) -> None:
    """
    Write a histogram to an HDF5 group. Arrays larger than
    `min_compress_elements` will be compressed; set to 0 to compress all
    arrays. The `compression` and `compression_opts` arguments are passed
    through.
    """
    histogram = _convert_input(histogram)
    # All referenced objects will be stored inside of /{name}/ref_axes
    hist_folder_storage = grp.create_group("ref_axes")

    # UHI version number
    grp.attrs["uhi_schema"] = histogram["uhi_schema"]

    _handle_metadata_writer_info(
        grp, histogram.get("metadata"), histogram.get("writer_info")
    )

    # Axes
    axes_dataset = grp.create_dataset(
        "axes", len(histogram["axes"]), dtype=h5py.special_dtype(ref=h5py.Reference)
    )
    for i, axis in enumerate(histogram["axes"]):
        # Iterating through the axes, calling `create_axes_object` for each of them,
        # creating references to new groups and appending it to the `items` dataset defined above
        ax_group = hist_folder_storage.create_group(f"axis_{i}")
        ax_info = axis.copy()
        ax_edges_raw = ax_info.pop("edges", None)
        ax_edges = np.asarray(ax_edges_raw) if ax_edges_raw is not None else None
        ax_cats: list[int] | list[str] | None = ax_info.pop("categories", None)
        _handle_metadata_writer_info(
            ax_group, ax_info.pop("metadata", None), ax_info.pop("writer_info", None)
        )
        for key, val2 in ax_info.items():
            ax_group.attrs[key] = val2
        if ax_edges is not None:
            if ax_edges.size < min_compress_elements:
                ax_group.create_dataset("edges", data=ax_edges)
            else:
                ax_group.create_dataset(
                    "edges",
                    data=ax_edges,
                    compression=compression,
                    compression_opts=compression_opts,
                )
        if ax_cats is not None:
            if len(ax_cats) < min_compress_elements:
                ax_group.create_dataset("categories", data=ax_cats)
            else:
                ax_group.create_dataset(
                    "categories",
                    data=ax_cats,
                    compression=compression,
                    compression_opts=compression_opts,
                )
        axes_dataset[i] = ax_group.ref

    # Storage
    storage_grp = grp.create_group("storage")
    storage_type = histogram["storage"]["type"]

    storage_grp.attrs["type"] = storage_type

    for key, val3 in histogram["storage"].items():
        if key == "type":
            continue
        npvalue = np.asarray(val3)
        if npvalue.size < min_compress_elements:
            storage_grp.create_dataset(key, data=npvalue)
        else:
            storage_grp.create_dataset(
                key,
                data=npvalue,
                compression=compression,
                compression_opts=compression_opts,
            )


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


def _read_metadata_writer_info(
    output: AnyHistogramIR | AnyAxisIR, group: h5py.Group | h5py.Dataset | h5py.Datatype
) -> None:
    if "metadata" in group:
        output["metadata"] = _convert_item("metadata", group["metadata"].attrs)
    if "writer_info" in group:
        output["writer_info"] = {
            k: _convert_item("metadata", v.attrs)
            for k, v in group["writer_info"].items()
        }


def _convert_axes(group: h5py.Group | h5py.Dataset | h5py.Datatype) -> AnyAxisIR:
    """
    Convert an HDF5 axis reference to a dictionary.
    """
    assert isinstance(group, h5py.Group)

    axis = typing.cast(
        AnyAxisIR, {k: _convert_item(k, v) for k, v in group.attrs.items()}
    )
    if "edges" in group:
        edges = group["edges"]
        assert isinstance(edges, h5py.Dataset)
        axis["edges"] = np.asarray(edges)
    if "categories" in group:
        categories = group["categories"]
        assert isinstance(categories, h5py.Dataset)
        axis["categories"] = [_convert_item("", c) for c in categories]

    _read_metadata_writer_info(axis, group)

    return axis


def read(grp: h5py.Group, /) -> HistogramIR:
    """
    Read a histogram from an HDF5 group.
    """
    uhi_schema = _convert_item("", grp.attrs["uhi_schema"])
    _check_uhi_schema_version(uhi_schema)

    axes_grp = grp["axes"]
    axes_ref = grp["ref_axes"]
    assert isinstance(axes_ref, h5py.Group)
    assert isinstance(axes_grp, h5py.Dataset)

    axes = [_convert_axes(axes_ref[unref_axis_ref]) for unref_axis_ref in axes_ref]

    storage_grp = grp["storage"]
    assert isinstance(storage_grp, h5py.Group)
    storage = AnyStorageIR(type=storage_grp.attrs["type"])
    for key in storage_grp:
        storage[key] = np.asarray(storage_grp[key])  # type: ignore[literal-required]

    histogram_dict = AnyHistogramIR(uhi_schema=uhi_schema, axes=axes, storage=storage)
    _read_metadata_writer_info(histogram_dict, grp)

    return histogram_dict  # type: ignore[return-value]
