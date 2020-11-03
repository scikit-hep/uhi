"""
Using the protocol:

Plotters should see if .effective_entries() is None - if not, this is a Profile
Then check .variances; if not None, this storage holds variance information and
error bars should be included. If it is None, then a plotter can avoid showing
error bars (recommended), or use np.sqrt(h.values()).
"""


# from numpy.typing import ArrayLike # requires unreleased NumPy 1.20
from typing import Any, Iterable, Optional, Protocol, Sequence, Tuple, Union
from typing import runtime_checkable

ArrayLike = Iterable[float]


@runtime_checkable
class PlottableAxis(Protocol):
    # label: str - Optional, not part of Protocol

    # True if the axis "wraps around"
    circular: bool

    # True if each bin is discrete - Integer, Boolean, or Category, for example
    discrete: bool

    def __getitem__(self, index: int) -> Union[Tuple[float, float], int, str]:
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


@runtime_checkable
class PlottableHistogram(Protocol):
    axes: Sequence[PlottableAxis]

    def values(self) -> ArrayLike:
        """
        Values returns the array or the values array for specialized
        accumulators.

        All methods can have a flow=False argument - not part of Protocol.
        """

    def variances(self) -> Optional[ArrayLike]:
        """
        Variance returns the variance if applicable, otherwise None.

        If counts is none, variance returns NaN for that cell (mean storages).
        """

    def effective_entries(self) -> Optional[ArrayLike]:
        """
        Count returns the number of values in a mean accumulator (also known as
        a Profile histogram), or is None for normal storages.
        """
