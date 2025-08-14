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
from typing import Any, Literal, Protocol, TypedDict, Union

from numpy.typing import ArrayLike

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required
else:
    from typing import NotRequired, Required

__all__ = [
    "AnyAxis",
    "AnyHistogram",
    "AnyStorage",
    "Axis",
    "BooleanAxis",
    "CategoryIntAxis",
    "CategoryStrAxis",
    "DoubleStorage",
    "Histogram",
    "IntStorage",
    "MeanStorage",
    "RegularAxis",
    "Storage",
    "ToUHIHistogram",
    "VariableAxis",
    "WeightedMeanStorage",
    "WeightedStorage",
]

SupportedMetadata = Union[float, str, bool]


def __dir__() -> list[str]:
    return __all__


class RegularAxis(TypedDict):
    type: Literal["regular"]
    lower: float
    upper: float
    bins: int
    underflow: bool
    overflow: bool
    circular: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class VariableAxis(TypedDict):
    type: Literal["variable"]
    edges: ArrayLike
    underflow: bool
    overflow: bool
    circular: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class CategoryStrAxis(TypedDict):
    type: Literal["category_str"]
    categories: list[str]
    flow: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class CategoryIntAxis(TypedDict):
    type: Literal["category_int"]
    categories: list[int]
    flow: bool
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class BooleanAxis(TypedDict):
    type: Literal["boolean"]
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class IntStorage(TypedDict):
    type: Literal["int"]
    values: ArrayLike


class DoubleStorage(TypedDict):
    type: Literal["double"]
    values: ArrayLike


class WeightedStorage(TypedDict):
    type: Literal["weighted"]
    values: ArrayLike
    variances: ArrayLike


class MeanStorage(TypedDict):
    type: Literal["mean"]
    counts: ArrayLike
    values: ArrayLike
    variances: ArrayLike


class WeightedMeanStorage(TypedDict):
    type: Literal["weighted_mean"]
    sum_of_weights: ArrayLike
    sum_of_weights_squared: ArrayLike
    values: ArrayLike
    variances: ArrayLike


Storage = Union[
    IntStorage, DoubleStorage, WeightedStorage, MeanStorage, WeightedMeanStorage
]

Axis = Union[RegularAxis, VariableAxis, CategoryStrAxis, CategoryIntAxis, BooleanAxis]


class AnyStorage(TypedDict, total=False):
    type: Required[Literal["int", "double", "weighted", "mean", "weighted_mean"]]
    values: ArrayLike
    variances: ArrayLike
    sum_of_weights: ArrayLike
    sum_of_weights_squared: ArrayLike
    counts: ArrayLike


class AnyAxis(TypedDict, total=False):
    type: Required[
        Literal["regular", "variable", "category_str", "category_int", "boolean"]
    ]
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, dict[str, SupportedMetadata]]
    lower: float
    upper: float
    bins: int
    edges: ArrayLike
    categories: list[str] | list[int]
    underflow: bool
    overflow: bool
    flow: bool
    circular: bool


class Histogram(TypedDict):
    uhi_schema: int
    axes: list[Axis]
    storage: Storage
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


class AnyHistogram(TypedDict):
    uhi_schema: int
    axes: list[AnyAxis]
    storage: AnyStorage
    metadata: NotRequired[dict[str, SupportedMetadata]]
    writer_info: NotRequired[dict[str, dict[str, SupportedMetadata]]]


@typing.runtime_checkable
class ToUHIHistogram(Protocol):
    def _to_uhi_(self) -> dict[str, Any]: ...
