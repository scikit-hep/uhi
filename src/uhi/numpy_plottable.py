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

from __future__ import annotations

import abc
import enum
import typing
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any

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
    _traits: PlottableTraits = typing.cast(Traits, None)


class NumPyPlottableAxis:
    def __init__(self, edges: np.typing.NDArray[Any]) -> None:
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

    def __getitem__(self, index: int) -> tuple[float, float]:
        """
        Get the pair of edges (not discrete) or bin label (discrete).
        """

        return tuple(self.edges[index])  # type: ignore[return-value]

    def __len__(self) -> int:
        """
        Return the number of bins (not counting flow bins, which are ignored
        for this Protocol currently).
        """
        return self.edges.shape[0]

    def __eq__(self, other: Any) -> bool:
        """
        Needed for the protocol (should be present to be stored in a Sequence).
        """
        return np.allclose(self.edges, other.edges)

    def __iter__(self) -> Iterator[tuple[float, float]]:
        """
        A useful part of the Protocol for easy access by plotters.
        """
        return iter(self[t] for t in range(len(self)))


if TYPE_CHECKING:
    _axis: PlottableAxisGeneric[tuple[float, float]] = typing.cast(
        NumPyPlottableAxis, None
    )


def _bin_helper(shape: int, bins: np.typing.NDArray[Any] | None) -> NumPyPlottableAxis:
    """
    Returns a axis built from the input bins array, which can be None (0 to N),
    2D lower, upper edges), or 1D (N+1 in length).
    """
    if bins is None:
        return NumPyPlottableAxis(
            np.array([np.arange(0, shape), np.arange(1, shape + 1)]).T
        )
    if bins.ndim == 2:
        return NumPyPlottableAxis(bins)
    if bins.ndim == 1:
        return NumPyPlottableAxis(np.array([bins[:-1], bins[1:]]).T)
    msg = "Bins not understood, should be 2d array of min/max edges or 1D array of edges or None"
    raise ValueError(msg)


class NumPyPlottableHistogram:
    def __init__(
        self,
        hist: np.typing.NDArray[Any],
        *bins: (
            np.typing.NDArray[Any] | None | tuple[np.typing.NDArray[Any] | None, ...]
        ),
        variances: np.typing.NDArray[Any] | None = None,
        kind: Kind = Kind.COUNT,
    ) -> None:
        self._values = hist
        self._variances = variances

        if len(bins) == 1 and isinstance(bins[0], tuple):
            (bins,) = bins  # type: ignore[assignment]

        if len(bins) == 0:
            bins = tuple([None] * len(hist.shape))

        self.kind = kind
        self.axes: Sequence[PlottableAxis] = [
            _bin_helper(shape, b) for shape, b in zip(hist.shape, bins)  # type: ignore[arg-type]
        ]

    def __repr__(self) -> str:
        """
        Just to be nice for debugging. Not required for the Protocol.
        """

        axes = ", ".join(repr(s) for s in self.axes)
        return f"{self.__class__.__name__}({self._values!r}, <{axes}>)"

    def values(self) -> np.typing.NDArray[Any]:
        return self._values

    def counts(self) -> np.typing.NDArray[Any]:
        return self._values

    def variances(self) -> np.typing.NDArray[Any] | None:
        return self._variances


if TYPE_CHECKING:
    # Verify that the above class is a valid PlottableHistogram
    _: PlottableHistogram = typing.cast(NumPyPlottableHistogram, None)


def _roottarray_asnumpy(
    tarr: Any, shape: tuple[int, ...] | None = None
) -> np.typing.NDArray[Any]:
    llv = tarr.GetArray()
    arr: np.typing.NDArray[Any] = np.frombuffer(
        llv, dtype=llv.typecode, count=tarr.GetSize()
    )
    if shape is not None:
        return np.reshape(arr, shape, order="F")
    return arr


class ROOTAxis(abc.ABC):
    def __init__(self, tAxis: Any) -> None:
        self.tAx = tAxis

    def __len__(self) -> int:
        return self.tAx.GetNbins()  # type: ignore[no-any-return]

    @abc.abstractmethod
    def __getitem__(self, index: int) -> Any:
        pass

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ROOTAxis):
            return NotImplemented
        return len(self) == len(other) and all(
            aEdges == bEdges for aEdges, bEdges in zip(self, other)
        )

    @abc.abstractmethod
    def __iter__(self) -> Iterator[tuple[float, float]] | Iterator[str]:
        pass

    @staticmethod
    def create(tAx: Any) -> DiscreteROOTAxis | ContinuousROOTAxis:
        if all(tAx.GetBinLabel(i + 1) for i in range(tAx.GetNbins())):
            return DiscreteROOTAxis(tAx)
        return ContinuousROOTAxis(tAx)


class ContinuousROOTAxis(ROOTAxis):
    @property
    def traits(self) -> PlottableTraits:
        return Traits(circular=False, discrete=False)

    def __getitem__(self, index: int) -> tuple[float, float]:
        return (self.tAx.GetBinLowEdge(index + 1), self.tAx.GetBinUpEdge(index + 1))

    def __iter__(self) -> Iterator[tuple[float, float]]:
        for i in range(len(self)):
            yield self[i]


class DiscreteROOTAxis(ROOTAxis):
    @property
    def traits(self) -> PlottableTraits:
        return Traits(circular=False, discrete=True)

    def __getitem__(self, index: int) -> str:
        return self.tAx.GetBinLabel(index + 1)  # type: ignore[no-any-return]

    def __iter__(self) -> Iterator[str]:
        for i in range(len(self)):
            yield self[i]


class ROOTPlottableHistBase:
    """Common base for ROOT histograms and TProfile"""

    def __init__(self, thist: Any) -> None:
        self.thist: Any = thist
        nDim = thist.GetDimension()
        self._shape: tuple[int, ...] = tuple(
            getattr(thist, f"GetNbins{ax}")() + 2 for ax in "XYZ"[:nDim]
        )
        self.axes: tuple[ContinuousROOTAxis | DiscreteROOTAxis, ...] = tuple(
            ROOTAxis.create(getattr(thist, f"Get{ax}axis")()) for ax in "XYZ"[:nDim]
        )

    @property
    def name(self) -> str:
        return self.thist.GetName()  # type: ignore[no-any-return]


class ROOTPlottableHistogram(ROOTPlottableHistBase):
    def __init__(self, thist: Any) -> None:
        super().__init__(thist)

    @property
    def hasWeights(self) -> bool:
        return bool(self.thist.GetSumw2() and self.thist.GetSumw2N())

    @property
    def kind(self) -> str:
        return Kind.COUNT

    def values(self) -> np.typing.NDArray[Any]:
        return _roottarray_asnumpy(self.thist, shape=self._shape)[
            tuple([slice(1, -1)] * len(self._shape))
        ]

    def variances(self) -> np.typing.NDArray[Any]:
        if self.hasWeights:
            return _roottarray_asnumpy(self.thist.GetSumw2(), shape=self._shape)[
                tuple([slice(1, -1)] * len(self._shape))
            ]
        return self.values()

    def counts(self) -> np.typing.NDArray[Any]:
        if not self.hasWeights:
            return self.values()

        sumw = self.values()
        return np.divide(
            sumw**2,
            self.variances(),
            out=np.zeros_like(sumw, dtype=np.float64),
            where=sumw != 0,
        )


class ROOTPlottableProfile(ROOTPlottableHistBase):
    def __init__(self, thist: Any) -> None:
        super().__init__(thist)

    @property
    def kind(self) -> str:
        return Kind.MEAN

    def values(self) -> np.typing.NDArray[Any]:
        return np.array(
            [self.thist.GetBinContent(i) for i in range(self.thist.GetNcells())]
        ).reshape(self._shape, order="F")[tuple([slice(1, -1)] * len(self._shape))]

    def variances(self) -> np.typing.NDArray[Any]:
        return (
            np.array([self.thist.GetBinError(i) for i in range(self.thist.GetNcells())])
            ** 2
        ).reshape(self._shape, order="F")[tuple([slice(1, -1)] * len(self._shape))]

    def counts(self) -> np.typing.NDArray[Any]:
        sumw = _roottarray_asnumpy(self.thist, shape=self._shape)[
            tuple([slice(1, -1)] * len(self._shape))
        ]
        if not (self.thist.GetSumw2() and self.thist.GetSumw2N()):
            return sumw

        sumw2 = _roottarray_asnumpy(self.thist.GetSumw2(), shape=self._shape)[
            tuple([slice(1, -1)] * len(self._shape))
        ]
        return np.divide(
            sumw**2,
            sumw2,
            out=np.zeros_like(sumw, dtype=np.float64),
            where=sumw != 0,
        )


if TYPE_CHECKING:
    # Verify that the above class is a valid PlottableHistogram
    _axis = typing.cast(ContinuousROOTAxis, None)
    _axis2: PlottableAxisGeneric[str] = typing.cast(DiscreteROOTAxis, None)
    _ = typing.cast(ROOTPlottableHistogram, None)
    _ = typing.cast(ROOTPlottableProfile, None)


def ensure_plottable_histogram(hist: Any) -> PlottableHistogram:
    """
    Ensure a histogram follows the PlottableHistogram Protocol.

    Currently supports adapting the following inputs:
    * .to_numpy() objects
    * .numpy() objects (uproot3/ROOT)
    * A tuple of NumPy style input. If dd style tuple, must contain
      "np.typing.NDArray[Any]"s. It can contain None's instead of values, including just
      a single None for any number of axes.
    """
    if isinstance(hist, PlottableHistogram):
        # Already satisfies the Protocol
        return hist

    if hasattr(hist, "to_numpy"):
        # Generic (possibly Uproot 4)
        _tup1: tuple[np.typing.NDArray[Any], ...] = hist.to_numpy(flow=False)
        return NumPyPlottableHistogram(*_tup1)

    if hasattr(hist, "numpy"):
        # uproot/TH1 - TODO: could support variances
        _tup2: tuple[np.typing.NDArray[Any], ...] = hist.numpy()
        return NumPyPlottableHistogram(*_tup2)

    if isinstance(hist, tuple):
        # NumPy histogram tuple
        if len(hist) < 2:
            msg = "Can't be applied to less than 2D tuple"
            raise TypeError(msg)
        if (
            len(hist) == 2
            and isinstance(hist[1], (list, tuple))
            and all(isinstance(h, np.ndarray) for h in hist[1])
        ):
            # histogramdd tuple
            return NumPyPlottableHistogram(
                np.asarray(hist[0]), *(np.asarray(h) for h in hist[1])
            )
        if hist[1] is None:
            return NumPyPlottableHistogram(
                np.asarray(hist[0]), *(None for _ in np.asarray(hist[0]).shape)
            )
        # Standard tuple
        return NumPyPlottableHistogram(*(np.asarray(h) for h in hist))

    if hasattr(hist, "InheritsFrom") and hist.InheritsFrom("TH1"):
        if any(
            hist.InheritsFrom(profCls)
            for profCls in ("TProfile", "TProfile2D", "TProfile3D")
        ):
            return ROOTPlottableProfile(hist)

        return ROOTPlottableHistogram(hist)

    msg = f"Can't be used on this type of object: {hist!r}"
    raise TypeError(msg)
