from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, TypedDict

__all__ = [
    "BooleanAxis",
    "CategoryIntAxis",
    "CategoryStrAxis",
    "DoubleStorage",
    "Histogram",
    "IntStorage",
    "MeanData",
    "MeanStorage",
    "RegularAxis",
    "VariableAxis",
    "WeighedData",
    "WeightedMeanData",
    "WeightedMeanStorage",
    "WeightedStorage",
]


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
    metadata: dict[str, Any]


class _RequiredVariableAxis(TypedDict):
    type: Literal["variable"]
    edges: list[float] | str
    underflow: bool
    overflow: bool
    circular: bool


class VariableAxis(_RequiredVariableAxis, total=False):
    metadata: dict[str, Any]


class _RequiredCategoryStrAxis(TypedDict):
    type: Literal["category_str"]
    categories: list[str]
    flow: bool


class CategoryStrAxis(_RequiredCategoryStrAxis, total=False):
    metadata: dict[str, Any]


class _RequiredCategoryIntAxis(TypedDict):
    type: Literal["category_int"]
    categories: list[int]
    flow: bool


class CategoryIntAxis(_RequiredCategoryIntAxis, total=False):
    metadata: dict[str, Any]


class _RequiredBooleanAxis(TypedDict):
    type: Literal["boolean"]


class BooleanAxis(_RequiredBooleanAxis, total=False):
    metadata: dict[str, Any]


class IntStorage(TypedDict):
    type: Literal["int"]
    data: str | Sequence[int]


class DoubleStorage(TypedDict):
    type: Literal["double"]
    data: str | Sequence[float]


class WeighedData(TypedDict):
    values: Sequence[float]
    variances: Sequence[float]


class WeightedStorage(TypedDict):
    type: Literal["weighted"]
    data: str | WeighedData


class MeanData(TypedDict):
    counts: Sequence[float]
    values: Sequence[float]
    variances: Sequence[float]


class MeanStorage(TypedDict):
    type: Literal["mean"]
    data: str | MeanData


class WeightedMeanData(TypedDict):
    sum_of_weights: Sequence[float]
    sum_of_weights_squared: Sequence[float]
    values: Sequence[float]
    variances: Sequence[float]


class WeightedMeanStorage(TypedDict):
    type: Literal["weighted_mean"]
    data: str | WeightedMeanData


class _RequiredHistogram(TypedDict):
    axes: list[
        RegularAxis | VariableAxis | CategoryStrAxis | CategoryIntAxis | BooleanAxis
    ]
    storage: (
        IntStorage | DoubleStorage | WeightedStorage | MeanStorage | WeightedMeanStorage
    )


class Histogram(_RequiredHistogram, total=False):
    metadata: dict[str, Any]
