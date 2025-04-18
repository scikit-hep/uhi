from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict, Union

__all__ = [
    "BooleanAxis",
    "CategoryIntAxis",
    "CategoryStrAxis",
    "DoubleStorage",
    "Histogram",
    "IntStorage",
    "MeanStorage",
    "RegularAxis",
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
    edges: list[float] | str
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
    values: Sequence[int] | str


class DoubleStorage(TypedDict):
    type: Literal["double"]
    values: Sequence[float] | str


class WeightedStorage(TypedDict):
    type: Literal["weighted"]
    values: Sequence[float] | str
    variances: Sequence[float] | str


class MeanStorage(TypedDict):
    type: Literal["mean"]
    counts: Sequence[float] | str
    values: Sequence[float] | str
    variances: Sequence[float] | str


class WeightedMeanStorage(TypedDict):
    type: Literal["weighted_mean"]
    sum_of_weights: Sequence[float] | str
    sum_of_weights_squared: Sequence[float] | str
    values: Sequence[float] | str
    variances: Sequence[float] | str


class _RequiredHistogram(TypedDict):
    axes: list[
        RegularAxis | VariableAxis | CategoryStrAxis | CategoryIntAxis | BooleanAxis
    ]
    storage: (
        IntStorage | DoubleStorage | WeightedStorage | MeanStorage | WeightedMeanStorage
    )


class Histogram(_RequiredHistogram, total=False):
    metadata: dict[str, SupportedMetadata]
    writer_info: dict[str, SupportedMetadata]
