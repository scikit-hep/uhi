from __future__ import annotations

import copy
import sys
from typing import Any, TypeVar

import numpy as np

from ..typing.serialization import AnyHistogramIR, AxisIR, HistogramIR

if sys.version_info < (3, 11):
    from typing_extensions import assert_never
else:
    from typing import assert_never


__all__ = ["ARRAY_KEYS", "LIST_KEYS", "from_sparse", "remove_writer_info", "to_sparse"]

ARRAY_KEYS = frozenset(
    [
        "index",
        "values",
        "variances",
        "edges",
        "counts",
        "sum_of_weights",
        "sum_of_weights_squared",
    ]
)

LIST_KEYS = frozenset(
    [
        "categories",
    ]
)

T = TypeVar("T", bound="dict[str, Any]")
H = TypeVar("H", bound="dict[str, Any] | HistogramIR | AnyHistogramIR")


def remove_writer_info(obj: T, /, *, library: str | None) -> T:
    """
    Removes all ``writer_info`` for a library from a histogram dict, axes dict,
    or storage dict. Makes copies where required, and the outer dictionary is
    always copied.

    Specify a library name, or ``None`` to remove all.
    """

    obj = copy.copy(obj)
    if library is None:
        obj.pop("writer_info", None)
    elif library in obj.get("writer_info", {}):
        obj["writer_info"] = copy.copy(obj["writer_info"])
        del obj["writer_info"][library]

    if "axes" in obj:
        obj["axes"] = [remove_writer_info(ax, library=library) for ax in obj["axes"]]
    if "storage" in obj:
        obj["storage"] = remove_writer_info(obj["storage"], library=library)

    return obj


def _compute_axis_length(axis: AxisIR) -> int:
    match axis["type"]:
        case "regular":
            return axis["bins"] + axis["underflow"] + axis["overflow"]
        case "variable":
            return len(axis["edges"]) - 1 + axis["underflow"] + axis["overflow"]
        case "category_str" | "category_int":
            return len(axis["categories"]) + axis["flow"]
        case "boolean":
            return 2
        case unreachable:
            assert_never(unreachable)


def _empty_is_zero(storage_type: str, key: str) -> bool:
    """
    Returns True if empty bins should be represented as zero (the common case).
    Returns False for weighted_mean variances, which use NaN to distinguish
    empty bins from bins with zero variance.
    """

    return storage_type != "weighted_mean" or key != "variances"


def to_sparse(hist: H, /) -> H:
    """
    Convert a dense histogram to a sparse one. Leaves a sparse histogram alone.
    Leaves empty (metadata-only) histograms alone.
    """

    storage = hist["storage"]
    storage_type = storage["type"]

    # Ignore histograms that have 0 dimensions, are already sparse, or are empty
    if "index" in storage or not hist["axes"] or len(storage) == 1:
        return hist

    # Get the arrays inside storage, ignoring "type"
    arrays = {k: np.asarray(v) for k, v in storage.items() if k != "type"}

    # Build mask of nonzero bins across *all* present keys
    mask = np.any(
        [
            arr != 0 if _empty_is_zero(storage_type, k) else ~np.isnan(arr)
            for k, arr in arrays.items()
        ],
        axis=0,
    )

    # Get the flat indices (or unravel them)
    nonzero_indices = np.nonzero(mask)

    # Pack indices into a single (ndim, n_nonzero) array
    index = np.vstack(nonzero_indices)

    # Build sparse storage dict
    sparse_storage = {"type": storage_type, "index": index}
    for k, arr in arrays.items():
        sparse_storage[k] = arr[mask]

    # Return new histogram dict with modified storage
    sparse_hist = copy.copy(hist)
    sparse_hist["storage"] = sparse_storage  # type: ignore[arg-type]
    return sparse_hist


def from_sparse(sparse: H, /) -> H:
    """
    Convert sparse histogram data back to dense format. If the histogram is already
    dense, just return it.
    """

    storage = sparse["storage"]
    storage_type = storage["type"]

    index = storage.get("index")
    if index is None:
        return sparse

    ndim, _n_nonzero = index.shape
    shape = [_compute_axis_length(a) for a in sparse["axes"]]  # type: ignore[arg-type]

    if len(shape) != ndim:
        msg = f"Shape {shape} does not match sparse index dimension {ndim}"
        raise ValueError(msg)

    dense_storage = {"type": storage["type"]}
    for k, arr1d in storage.items():
        if k in {"index", "type"}:
            continue
        arr1dnp = np.asarray(arr1d)

        # Allocate a zeros (or nan) array of the original shape
        full = np.full(
            shape, 0 if _empty_is_zero(storage_type, k) else np.nan, dtype=arr1dnp.dtype
        )

        # Scatter sparse values back into dense array
        full[tuple(index)] = arr1dnp
        dense_storage[k] = full

    retval = copy.copy(sparse)
    retval["storage"] = dense_storage  # type: ignore[arg-type]
    return retval
