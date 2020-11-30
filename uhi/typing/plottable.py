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
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from typing import runtime_checkable

# from numpy.typing import ArrayLike # requires unreleased NumPy 1.20
ArrayLike = Iterable[float]

# Known kinds of histograms. A Producer can add types not defined here; a
# Consumer should check for known types if it matters.
# Interpretation = Literal["count", "mean"] - left as a generic string so it
# can be added to.
Interpretation = str

# Implementations are highly encouraged to use the following construct:
# class Interpretation(str, enum.Enum):
#     count = "count"
#     mean = "mean"

@runtime_checkable
class PlottableTraits(Protocol):
    # True if the axis "wraps around"
    circular: bool

    # True if each bin is discrete - Integer, Boolean, or Category, for example
    discrete: bool


T = TypeVar("T", covariant=True)


@runtime_checkable
class PlottableAxisGeneric(Protocol[T]):
    # label: str - Optional, not part of Protocol

    traits: PlottableTraits

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

    interpretation: Interpretation

    def values(self) -> ArrayLike:
        """
        Values returns the array or the values array for specialized
        accumulators.

        All methods can have a flow=False argument - not part of Protocol.
        """

    def variances(self) -> Optional[ArrayLike]:
        """
        Variance returns the variance of the values (for mean histograms, this
        is not the variance of the counts). If unweighed, this returns None.

        If counts is less than 2, the variance in that cell is undefined for mean storages.
        """

    def counts(self) -> ArrayLike:
        """
        Count returns the number of values counted in a mean accumulator (also
        known as a Profile histogram), or is identical to .values if
        interpretation is "count".
        """
