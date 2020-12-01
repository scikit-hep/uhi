"""
Using the protocol:

Producers: use isinstance(myhist, PlottableHistogram) in your tests; part of
the protocol is checkable at runtime, though ideally you should use MyPy; if
your histogram class supports PlottableHistogram, this will pass.

Consumers: Make your functions accept the PlottableHistogram static type, and
MyPy will force you to only use items in the Protocol.
"""

protocol_version = 1


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

# Known kinds of histograms. A Producer can add Kinds not defined here; a
# Consumer should check for known types if it matters. A simple plotter could
# just use .value and .variance if non-None and ignore .kind.
#
# Could have been Kind = Literal["COUNT", "MEAN"] - left as a generic string so
# it can be extendable.
Kind = str

# Implementations are highly encouraged to use the following construct:
# class Kind(str, enum.Enum):
#     COUNT = "COUNT"
#     MEAN = "MEAN"
# Then return and use Kind.COUNT or Kind.MEAN.

@runtime_checkable
class PlottableTraits(Protocol):
    # True if the axis "wraps around"
    circular: bool

    # True if each bin is discrete - Integer, Boolean, or Category, for example
    discrete: bool


T = TypeVar("T", covariant=True)


@runtime_checkable
class PlottableAxisGeneric(Protocol[T]):
    # name: str - Optional, not part of Protocol
    # label: str - Optional, not part of Protocol
    #
    # Plotters are encouraged to plot label if it exists and is not None, and
    # name otherwise if it exists and is not None, but these properties are not
    # available on all histograms and not part of the Protocol.

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
        Values returns the counts for simple histograms or the mean for mean
        histograms.  If this has a "mean" interpretation, then values is
        undefined and left up to the Producer implementation if counts is less
        than 1. A Consumer should check counts before using this.

        All methods can have a flow=False argument - not part of Protocol.  If
        this is included, it should return an array with flow bins added,
        normal ordering.
        """

    def variances(self) -> Optional[ArrayLike]:
        """
        Variance returns the variance of the values (for "MEAN" histograms,
        this is not the variance of the counts, but the variance of the mean).
        If unweighed, this returns None.

        If counts is equal to 1 or less, the variance in that cell is undefined if
        kind=="MEAN".
        """

    def counts(self) -> Optional[ArrayLike]:
        """
        Count returns the effective number of entries. Current Kinds of common histograms
        all have a defined counts, but an exotic histogram could have a None .counts, so
        this is Optional and should be checked by Consumers.

        For a weighted histogram, counts is defined as sum_of_weights ** 2 /
        sum_of_weights_squared. It is always equal to or smaller than the
        number of times the histogram was filled. If there is no variance in
        the weights, this is exactly equal to the number of times this was
        filled. The larger the spread in weights, this is smaller, but always 0
        if filled 0 times, and 1 if filled once, and more than 1.

        A suggested implementation is:

            return np.divide(
                sum_of_weights**2,
                sum_of_weights_squared,
                out=np.zeros_like(sum_of_weights, dtype=np.float64),
                where=sum_of_weights_squared!=0)
        """
