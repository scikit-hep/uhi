"""
Common helpers for the different formats.
"""

from __future__ import annotations

__all__ = ["_check_uhi_schema_version", "_convert_input"]

from ..typing.serialization import AnyHistogramIR, ToUHIHistogram


def _check_uhi_schema_version(uhi_schema: int, /) -> None:
    if uhi_schema != 1:
        msg = "Only uhi_schema=1 supported in this uhi version. Please update uhi."
        raise TypeError(msg)


def _convert_input(hist: AnyHistogramIR | ToUHIHistogram, /) -> AnyHistogramIR:
    any_hist = hist._to_uhi_() if isinstance(hist, ToUHIHistogram) else hist
    _check_uhi_schema_version(any_hist["uhi_schema"])
    return any_hist  # type: ignore[return-value]
