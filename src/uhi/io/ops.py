"""
Operations on histograms in the intermediate representation.
"""

from __future__ import annotations

import copy
import functools
import sys
from typing import Any

import numpy as np

from ..typing.serialization import (
    AnyAxisIR,
    AnyHistogramIR,
    AnyStorageIR,
    ToUHIHistogram,
)
from . import from_sparse, to_sparse
from ._common import _convert_input

if sys.version_info < (3, 11):
    from typing_extensions import assert_never
else:
    from typing import assert_never

__all__ = ["add"]


def __dir__() -> list[str]:
    return __all__


def _strip_axis(axis: AnyAxisIR, /) -> dict[str, Any]:
    return {k: v for k, v in axis.items() if k not in {"metadata", "writer_info"}}


def _axes_equal(a: AnyAxisIR, b: AnyAxisIR, /) -> bool:
    """
    Compare two axes, ignoring metadata and writer_info.
    """
    a_dict = _strip_axis(a)
    b_dict = _strip_axis(b)
    if a_dict.keys() != b_dict.keys():
        return False
    return all(
        np.array_equal(a_dict[k], b_dict[k]) if k == "edges" else a_dict[k] == b_dict[k]
        for k in a_dict
    )


def _add_mean(a: AnyStorageIR, b: AnyStorageIR, /) -> AnyStorageIR:
    """
    Merge two mean storages. ``variances`` holds the sample variance,
    ``M2 / (counts - 1)``, so it is converted back to ``M2`` (the sum of
    squared deviations) before merging with the parallel-variance formula.
    """
    n_a, n_b = np.asarray(a["counts"]), np.asarray(b["counts"])
    m_a, m_b = np.asarray(a["values"]), np.asarray(b["values"])
    v_a, v_b = np.asarray(a["variances"]), np.asarray(b["variances"])

    n = n_a + n_b
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.divide(
            n_a * m_a + n_b * m_b, n, out=np.zeros_like(n, dtype=float), where=n != 0
        )
        m2_a = np.where(np.isfinite(v_a), v_a * (n_a - 1), 0.0)
        m2_b = np.where(np.isfinite(v_b), v_b * (n_b - 1), 0.0)
        m2 = (
            m2_a
            + m2_b
            + np.divide(
                (m_a - m_b) ** 2 * n_a * n_b,
                n,
                out=np.zeros_like(n, dtype=float),
                where=n != 0,
            )
        )
        v = m2 / (n - 1)
    return {"type": "mean", "counts": n, "values": m, "variances": v}


def _add_weighted_mean(a: AnyStorageIR, b: AnyStorageIR, /) -> AnyStorageIR:
    """
    Merge two weighted_mean storages. ``variances`` holds
    ``M2 / (sum_of_weights - sum_of_weights_squared / sum_of_weights)``, so it
    is converted back to ``M2`` before merging.
    """
    w_a, w_b = np.asarray(a["sum_of_weights"]), np.asarray(b["sum_of_weights"])
    w2_a, w2_b = (
        np.asarray(a["sum_of_weights_squared"]),
        np.asarray(b["sum_of_weights_squared"]),
    )
    m_a, m_b = np.asarray(a["values"]), np.asarray(b["values"])
    v_a, v_b = np.asarray(a["variances"]), np.asarray(b["variances"])

    w = w_a + w_b
    w2 = w2_a + w2_b
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.divide(
            w_a * m_a + w_b * m_b, w, out=np.zeros_like(w, dtype=float), where=w != 0
        )
        d_a = w_a - np.divide(
            w2_a, w_a, out=np.zeros_like(w, dtype=float), where=w_a != 0
        )
        d_b = w_b - np.divide(
            w2_b, w_b, out=np.zeros_like(w, dtype=float), where=w_b != 0
        )
        m2_a = np.where(np.isfinite(v_a), v_a * d_a, 0.0)
        m2_b = np.where(np.isfinite(v_b), v_b * d_b, 0.0)
        m2 = (
            m2_a
            + m2_b
            + np.divide(
                (m_a - m_b) ** 2 * w_a * w_b,
                w,
                out=np.zeros_like(w, dtype=float),
                where=w != 0,
            )
        )
        v = m2 / (w - w2 / w)
    return {
        "type": "weighted_mean",
        "sum_of_weights": w,
        "sum_of_weights_squared": w2,
        "values": m,
        "variances": v,
    }


def _add_storage(a: AnyStorageIR, b: AnyStorageIR, /) -> AnyStorageIR:
    """
    Add two dense, non-empty storages of the same type.
    """
    match a["type"]:
        case "int" | "double":
            return {"type": a["type"], "values": np.add(a["values"], b["values"])}
        case "weighted":
            return {
                "type": "weighted",
                "values": np.add(a["values"], b["values"]),
                "variances": np.add(a["variances"], b["variances"]),
            }
        case "mean":
            return _add_mean(a, b)
        case "weighted_mean":
            return _add_weighted_mean(a, b)
        case unreachable:
            assert_never(unreachable)


def add(
    first: AnyHistogramIR | ToUHIHistogram, /, *rest: AnyHistogramIR | ToUHIHistogram
) -> AnyHistogramIR:
    """
    Add histograms bin-by-bin, like ROOT's ``hadd``. All histograms must have
    identical axes (metadata and ``writer_info`` are ignored in the
    comparison) and the same storage type. Empty (metadata-only) storages
    count as zero. Metadata and ``writer_info`` are taken from the first
    histogram.

    The result is sparse if every input is sparse, and dense otherwise.

    .. versionadded:: 1.2
    """
    hists = [_convert_input(h) for h in (first, *rest)]
    base = hists[0]

    for i, hist in enumerate(hists[1:], start=1):
        if hist["storage"]["type"] != base["storage"]["type"]:
            msg = f"Histogram {i} has storage type {hist['storage']['type']!r}, expected {base['storage']['type']!r}"
            raise ValueError(msg)
        # zip() is shadowed by the uhi.io.zip submodule, so index instead
        if len(hist["axes"]) != len(base["axes"]) or not all(
            _axes_equal(hist["axes"][j], base["axes"][j])
            for j in range(len(base["axes"]))
        ):
            msg = f"Histogram {i} has axes that do not match histogram 0"
            raise ValueError(msg)

    all_sparse = all("index" in h["storage"] for h in hists)
    storages = [from_sparse(h)["storage"] for h in hists]
    non_empty = [s for s in storages if len(s) > 1]

    if non_empty:
        storage = functools.reduce(_add_storage, non_empty)
    else:
        storage = AnyStorageIR(type=base["storage"]["type"])

    result = copy.copy(base)
    result["storage"] = storage
    return to_sparse(result) if all_sparse else result
