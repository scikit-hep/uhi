"""
This file holds the NumPyPlottableHistogram, meant to adapt any histogram that
does not support the PlottableHistogram Protocol into a NumPy-backed standin
for it, so plotting functions can remain simple and depend on having a
PlottableHistogram regardless of the input. And this comes with an adaptor
function, ensure_plottable_histogram, which will adapt common input types to a
NumPyPlottibleHistogram, and pass a valid PlottibleHistogram through.

Keep in mind, NumPyPlottableHistogram is a minimal PlottableHistogram instance,
and does not provide any further functionality and is not intended to be used
beyond plotting. Please see a full histogram library like boost-histogram or
hist.
"""

import enum
from typing import TYPE_CHECKING, Any, Iterator, Optional, Sequence, Tuple, Union, cast

import numpy as np

from uhi.typing.plottable import (
    PlottableAxis,
    PlottableAxisGeneric,
    PlottableHistogram,
    PlottableTraits,
)

if TYPE_CHECKING:
    from numpy.typing import ArrayLike
else:
    ArrayLike = Any


class Kind(str, enum.Enum):
    COUNT = "COUNT"
    MEAN = "MEAN"


class Traits:
    __slots__ = ("circular", "discrete")

    def __init__(self, *, circular: bool = False, discrete: bool = False) -> None:
        self.circular = circular
        self.discrete = discrete


if TYPE_CHECKING:
    _traits: PlottableTraits = cast(Traits, None)


class NumPyPlottableAxis:
    def __init__(self, edges: np.ndarray) -> None:
        """
        The vals should already be an Nx2 ndarray of edges.
        """
        self.traits: PlottableTraits = Traits()
        assert edges.ndim == 2, "Must be 2D array of edges"
        assert edges.shape[1] == 2, "Second dimension must be 2 (lower, upper)"
        self.edges = edges

    def __repr__(self) -> str:
        """
        Just to be nice for debugging. Not required for the Protocol.
        """

        return f"{self.__class__.__name__}({self.edges!r})"

    def __getitem__(self, index: int) -> Tuple[float, float]:
        """
        Get the pair of edges (not discrete) or bin label (discrete).
        """

        return tuple(self.edges[index])  # type: ignore

    def __len__(self) -> int:
        """
        Return the number of bins (not counting flow bins, which are ignored
        for this Protocol currently).
        """
        return self.edges.shape[0]  # type: ignore

    def __eq__(self, other: Any) -> bool:
        """
        Needed for the protocol (should be present to be stored in a Sequence).
        """
        return np.allclose(self.edges, other.edges)

    def __iter__(self) -> Iterator[Tuple[float, float]]:
        """
        A useful part of the Protocol for easy access by plotters.
        """
        return iter(self[t] for t in range(len(self)))


if TYPE_CHECKING:
    _axis: PlottableAxisGeneric[Tuple[float, float]] = cast(NumPyPlottableAxis, None)


def _bin_helper(shape: int, bins: Optional[np.ndarray]) -> NumPyPlottableAxis:
    """
    Returns a axis built from the input bins array, which can be None (0 to N),
    2D lower, upper edges), or 1D (N+1 in length).
    """
    if bins is None:
        return NumPyPlottableAxis(
            np.array([np.arange(0, shape), np.arange(1, shape + 1)]).T
        )
    elif bins.ndim == 2:
        return NumPyPlottableAxis(bins)
    elif bins.ndim == 1:
        return NumPyPlottableAxis(np.array([bins[:-1], bins[1:]]).T)
    else:
        raise ValueError(
            "Bins not understood, should be 2d array of min/max edges or 1D array of edges or None"
        )


class NumPyPlottableHistogram:
    def __init__(
        self,
        hist: np.ndarray,
        *bins: Union[np.ndarray, None, Tuple[Union[np.ndarray, None], ...]],
        variances: Optional[np.ndarray] = None,
        kind: Kind = Kind.COUNT,
    ) -> None:

        self._values = hist
        self._variances = variances

        if len(bins) == 1 and isinstance(bins[0], tuple):
            (bins,) = bins  # type: ignore

        if len(bins) == 0:
            bins = tuple([None] * len(hist.shape))

        self.kind = kind
        self.axes: Sequence[PlottableAxis] = [
            _bin_helper(shape, b) for shape, b in zip(hist.shape, bins)  # type: ignore
        ]

    def __repr__(self) -> str:
        """
        Just to be nice for debugging. Not required for the Protocol.
        """

        axes = ", ".join(repr(s) for s in self.axes)
        return f"{self.__class__.__name__}({self._values!r}, <{axes}>)"

    def values(self) -> np.ndarray:
        return self._values

    def counts(self) -> np.ndarray:
        return self._values

    def variances(self) -> Optional[np.ndarray]:
        return self._variances


if TYPE_CHECKING:
    # Verify that the above class is a valid PlottableHistogram
    _: PlottableHistogram = cast(NumPyPlottableHistogram, None)


def ensure_plottable_histogram(hist: Any) -> PlottableHistogram:
    """
    Ensure a histogram follows the PlottableHistogram Protocol.

    Currently supports adapting the following inputs:
    * .to_numpy() objects
    * .numpy() objects (uproot3/ROOT)
    * A tuple of NumPy style input. If dd style tuple, must contain
      np.ndarrays. It can contain None's instead of values, including just
      a single None for any number of axes.
    """
    if isinstance(hist, PlottableHistogram):
        # Already satisfies the Protocol
        return hist

    elif hasattr(hist, "to_numpy"):
        # Generic (possibly Uproot 4)
        _tup1: Tuple[np.ndarray, ...] = hist.to_numpy(flow=False)
        return NumPyPlottableHistogram(*_tup1)

    elif hasattr(hist, "numpy"):
        # uproot/TH1 - TODO: could support variances
        _tup2: Tuple[np.ndarray, ...] = hist.numpy()
        return NumPyPlottableHistogram(*_tup2)

    elif isinstance(hist, tuple):
        # NumPy histogram tuple
        if len(hist) < 2:
            raise TypeError("Can't be applied to less than 2D tuple")
        elif (
            len(hist) == 2
            and isinstance(hist[1], (list, tuple))
            and all(isinstance(h, np.ndarray) for h in hist[1])
        ):
            # histogramdd tuple
            return NumPyPlottableHistogram(
                np.asarray(hist[0]), *(np.asarray(h) for h in hist[1])
            )
        elif hist[1] is None:
            return NumPyPlottableHistogram(
                np.asarray(hist[0]), *(None for _ in np.asarray(hist[0]).shape)
            )
        else:
            # Standard tuple
            return NumPyPlottableHistogram(*(np.asarray(h) for h in hist))

    else:
        raise TypeError(f"Can't be used on this type of object: {hist!r}")
