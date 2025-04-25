"""Serialization types for UHI.

Two types of dictionaries are defined here:

1. ``AnyAxis``, ``AnyStorage``, and ``AnyHistogram`` are used for inputs. They represent
   the merger of all possible types.
2. ``Axis``, ``Storage``, and ``histogram`` are used for outputs. These have precise entries
   defined for each Literal type.
"""

from __future__ import annotations

from typing import Literal, TypedDict, Union

from numpy.typing import ArrayLike

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
    "VariableAxis",
    "WeightedMeanStorage",
    "WeightedStorage",
]

SupportedMetadata = Union[float, str, bool]


def __dir__() -> list[str]:
    return __all__


class _RequiredRegularAxis(TypedDict):
    type: Literal["regular"]
    lower: float
    upper: float
    bins: int
    underflow: bool
    overflow: bool
    circular: bool


class RegularAxis(_RequiredRegularAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class _RequiredVariableAxis(TypedDict):
    type: Literal["variable"]
    edges: ArrayLike | str
    underflow: bool
    overflow: bool
    circular: bool


class VariableAxis(_RequiredVariableAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class _RequiredCategoryStrAxis(TypedDict):
    type: Literal["category_str"]
    categories: list[str]
    flow: bool


class CategoryStrAxis(_RequiredCategoryStrAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class _RequiredCategoryIntAxis(TypedDict):
    type: Literal["category_int"]
    categories: list[int]
    flow: bool


class CategoryIntAxis(_RequiredCategoryIntAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class _RequiredBooleanAxis(TypedDict):
    type: Literal["boolean"]


class BooleanAxis(_RequiredBooleanAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class IntStorage(TypedDict):
    type: Literal["int"]
    values: ArrayLike | str


class DoubleStorage(TypedDict):
    type: Literal["double"]
    values: ArrayLike | str


class WeightedStorage(TypedDict):
    type: Literal["weighted"]
    values: ArrayLike | str
    variances: ArrayLike | str


class MeanStorage(TypedDict):
    type: Literal["mean"]
    counts: ArrayLike | str
    values: ArrayLike | str
    variances: ArrayLike | str


class WeightedMeanStorage(TypedDict):
    type: Literal["weighted_mean"]
    sum_of_weights: ArrayLike | str
    sum_of_weights_squared: ArrayLike | str
    values: ArrayLike | str
    variances: ArrayLike | str


Storage = Union[
    IntStorage, DoubleStorage, WeightedStorage, MeanStorage, WeightedMeanStorage
]

Axis = Union[RegularAxis, VariableAxis, CategoryStrAxis, CategoryIntAxis, BooleanAxis]


class _RequiredAnyStorage(TypedDict):
    type: Literal["int", "double", "weighted", "mean", "weighted_mean"]


class AnyStorage(_RequiredAnyStorage, total=False):
    values: ArrayLike | str
    variances: ArrayLike | str
    sum_of_weights: ArrayLike | str
    sum_of_weights_squared: ArrayLike | str
    counts: ArrayLike | str


class _RequiredAnyAxis(TypedDict):
    type: Literal["regular", "variable", "category_str", "category_int", "boolean"]


class AnyAxis(_RequiredAnyAxis, total=False):
    metadata: dict[str, SupportedMetadata]
    lower: float
    upper: float
    bins: int
    edges: ArrayLike | str
    categories: list[str] | list[int]
    underflow: bool
    overflow: bool
    flow: bool
    circular: bool


class _RequiredHistogram(TypedDict):
    axes: list[Axis]
    storage: Storage


class Histogram(_RequiredHistogram, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]


class _RequiredAnyHistogram(TypedDict):
    axes: list[AnyAxis]
    storage: AnyStorage


class AnyHistogram(_RequiredAnyHistogram, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]
