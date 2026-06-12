"""
Common helpers for the different formats.
"""

from __future__ import annotations

import typing

from ..typing.serialization import AnyAxisIR, AnyHistogramIR, ToUHIHistogram

__all__ = ["_check_uhi_schema_version", "_convert_input"]


def _check_uhi_schema_version(uhi_schema: int, /) -> None:
    if uhi_schema != 1:
        msg = "Only uhi_schema=1 supported in this uhi version. Please update uhi."
        raise TypeError(msg)


def _remove_empty_metadata(hist: AnyHistogramIR, /) -> AnyHistogramIR:
    if "metadata" in hist and not hist["metadata"]:
        hist = typing.cast(
            AnyHistogramIR, {k: v for k, v in hist.items() if k != "metadata"}
        )
    # Copy the axes list before reassigning elements so the caller's list is
    # not mutated in place.
    axes = list(hist["axes"])
    for i, axis in enumerate(axes):
        if "metadata" in axis and not axis["metadata"]:
            axes[i] = typing.cast(
                AnyAxisIR, {k: v for k, v in axis.items() if k != "metadata"}
            )
    return typing.cast(AnyHistogramIR, {**hist, "axes": axes})


def _convert_input(hist: AnyHistogramIR | ToUHIHistogram, /) -> AnyHistogramIR:
    any_hist = typing.cast(
        AnyHistogramIR, hist._to_uhi_() if isinstance(hist, ToUHIHistogram) else hist
    )
    _check_uhi_schema_version(any_hist["uhi_schema"])
    return _remove_empty_metadata(any_hist)
