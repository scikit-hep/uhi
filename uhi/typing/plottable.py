"""
Using the protocol:

Plotters should see if .counts() is None - if not, this is a Profile
Then check .variances; if not None, this storage holds variance information and
error bars should be included. If it is None, then a plotter can avoid showing
error bars (recommended), or use np.sqrt(h.values()).
"""


from typing import (
    Any,
    Iterable,
    Literal,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from typing import runtime_checkable

# from numpy.typing import ArrayLike # requires unreleased NumPy 1.20
ArrayLike = Iterable[float]


@runtime_checkable
class PlottableOptions(Protocol):
    # True if the axis "wraps around"
    circular: bool

    # True if each bin is discrete - Integer, Boolean, or Category, for example
    discrete: bool


T = TypeVar("T", covariant=True)


@runtime_checkable
class PlottableAxisGeneric(Protocol[T]):
    # label: str - Optional, not part of Protocol

    options: PlottableOptions

    def __getitem__(self, index: int) -> T:
        """
        Get the pair of edges (not discrete) or bin label (discrete).
        """

    def __len__(self) -> int:
        """
        Return the number of bins (not counting flow bins, which are ignored
        for this Protocol currently).
        """

    def __eq__(self, other: Any) -> bool:
        """
        Required to be sequence-like.
        """


PlottableAxisContinuous = PlottableAxisGeneric[Tuple[float, float]]
PlottableAxisInt = PlottableAxisGeneric[int]
PlottableAxisStr = PlottableAxisGeneric[str]

PlottableAxis = Union[PlottableAxisContinuous, PlottableAxisInt, PlottableAxisStr]


@runtime_checkable
class PlottableHistogram(Protocol):
    axes: Sequence[PlottableAxis]

    weighted: bool
    interpretation: Literal["count", "mean"]

    def values(self) -> ArrayLike:
        """
        Values returns the array or the values array for specialized
        accumulators.

        All methods can have a flow=False argument - not part of Protocol.
        """

    def variances(self) -> ArrayLike:
        """
        Variance returns the variance. If unweighed, this is identical to .counts().

        If counts is none, variance returns NaN for that cell (mean storages).
        """

    def counts(self) -> ArrayLike:
        """
        Count returns the number of values counted in a mean accumulator (also
        known as a Profile histogram), or is identical to .values if
        interpretation is "count".
        """
