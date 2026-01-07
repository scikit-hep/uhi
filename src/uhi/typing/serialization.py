"""Serialization types for UHI.

Two types of dictionaries are defined here:

1. ``AnyAxis``, ``AnyStorage``, and ``AnyHistogram`` are used for inputs. They represent
   the merger of all possible types.
2. ``Axis``, ``Storage``, and ``histogram`` are used for outputs. These have precise entries
   defined for each Literal type.

There's also a Protocol, `ToUHIHistogram`, for anything that supports conversion.
"""

from __future__ import annotations

import sys
import typing
from collections.abc import Sequence
from typing import Any, Literal, Protocol, TypedDict

import numpy as np
from numpy.typing import NDArray

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required
else:
    from typing import NotRequired, Required

__all__ = [
    "AnyAxisIR",
    "AnyHistogramIR",
    "AnyStorageIR",
    "AxisIR",
    "BooleanAxisIR",
    "CategoryIntAxisIR",
    "CategoryStrAxisIR",
    "DoubleStorageIR",
    "HistogramIR",
    "IntStorageIR",
    "MeanStorageIR",
    "RegularAxisIR",
    "StorageIR",
    "ToUHIHistogram",
    "VariableAxisIR",
    "WeightedMeanStorageIR",
    "WeightedStorageIR",
]

SupportedMetadata = float | str | bool

ArrayLikeFloat = Sequence[float] | NDArray[np.float64]


def __dir__() -> list[str]:
    return __all__


class RegularAxisIR(TypedDict):
    type: Literal["regular"]
    lower: float
    upper: float
    bins: int
    underflow: bool
    overflow: bool
    circular: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class VariableAxisIR(TypedDict):
    type: Literal["variable"]
    edges: ArrayLikeFloat
    underflow: bool
    overflow: bool
    circular: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class CategoryStrAxisIR(TypedDict):
    type: Literal["category_str"]
    categories: list[str]
    flow: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class CategoryIntAxisIR(TypedDict):
    type: Literal["category_int"]
    categories: list[int]
    flow: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class BooleanAxisIR(TypedDict):
    type: Literal["boolean"]
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class IntStorageIR(TypedDict):
    type: Literal["int"]
    values: NDArray[np.float64]
    index: NotRequired[NDArray[np.float64]]


class DoubleStorageIR(TypedDict):
    type: Literal["double"]
    values: NDArray[np.float64]
    index: NotRequired[NDArray[np.float64]]


class WeightedStorageIR(TypedDict):
    type: Literal["weighted"]
    values: NDArray[np.float64]
    variances: NDArray[np.float64]
    index: NotRequired[NDArray[np.float64]]


class MeanStorageIR(TypedDict):
    type: Literal["mean"]
    counts: NDArray[np.float64]
    values: NDArray[np.float64]
    variances: NDArray[np.float64]
    index: NotRequired[NDArray[np.float64]]


class WeightedMeanStorageIR(TypedDict):
    type: Literal["weighted_mean"]
    sum_of_weights: NDArray[np.float64]
    sum_of_weights_squared: NDArray[np.float64]
    values: NDArray[np.float64]
    variances: NDArray[np.float64]
    index: NotRequired[NDArray[np.float64]]


StorageIR = (
    IntStorageIR
    | DoubleStorageIR
    | WeightedStorageIR
    | MeanStorageIR
    | WeightedMeanStorageIR
)


AxisIR = (
    RegularAxisIR
    | VariableAxisIR
    | CategoryStrAxisIR
    | CategoryIntAxisIR
    | BooleanAxisIR
)


class AnyStorageIR(TypedDict, total=False):
    type: Required[Literal["int", "double", "weighted", "mean", "weighted_mean"]]
    index: NDArray[np.float64]
    values: NDArray[np.float64]
    variances: NDArray[np.float64]
    sum_of_weights: NDArray[np.float64]
    sum_of_weights_squared: NDArray[np.float64]
    counts: NDArray[np.float64]


class AnyAxisIR(TypedDict, total=False):
    type: Required[
        Literal["regular", "variable", "category_str", "category_int", "boolean"]
    ]
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, dict[str, SupportedMetadata]]
    lower: float
    upper: float
    bins: int
    edges: ArrayLikeFloat
    categories: list[str] | list[int]
    underflow: bool
    overflow: bool
    flow: bool
    circular: bool


class HistogramIR(TypedDict):
    uhi_schema: int
    axes: list[AxisIR]
    storage: StorageIR
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class AnyHistogramIR(TypedDict):
    uhi_schema: int
    axes: list[AnyAxisIR]
    storage: AnyStorageIR
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


@typing.runtime_checkable
class ToUHIHistogram(Protocol):
    def _to_uhi_(self) -> dict[str, Any]: ...
