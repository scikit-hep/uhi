from __future__ import annotations

import copy
import typing
from typing import Any

from .typing.plottable import PlottableAxis

__all__ = ["Locator", "Overflow", "Underflow", "at", "loc", "rebin"]


def __dir__() -> list[str]:
    return __all__


T = typing.TypeVar("T", bound="Locator")


class Locator:
    __slots__ = ("offset",)
    NAME = ""

    def __init__(self, offset: int = 0) -> None:
        if not isinstance(offset, int):
            msg = "The offset must be an integer"  # type: ignore[unreachable]
            raise ValueError(msg)

        self.offset = offset

    def __add__(self: T, offset: int) -> T:
        other = copy.copy(self)
        other.offset += offset
        return other

    def __sub__(self: T, offset: int) -> T:
        other = copy.copy(self)
        other.offset -= offset
        return other

    def _print_self_(self) -> str:
        return ""

    def __repr__(self) -> str:
        s = self.NAME or self.__class__.__name__
        s += self._print_self_()
        if self.offset != 0:
            s += " + " if self.offset > 0 else " - "
            s += str(abs(self.offset))
        return s

    if typing.TYPE_CHECKING:
        # Type checkers think that this is required
        def __index__(self) -> int:
            return 42


class loc(Locator):
    __slots__ = ("value",)

    def __init__(self, value: str | float, offset: int = 0) -> None:
        super().__init__(offset)
        self.value = value

    def _print_self_(self) -> str:
        return f"({self.value})"

    # TODO: clarify that .index() is required
    def __call__(self, axis: Any) -> int:
        return axis.index(self.value) + self.offset  # type: ignore[no-any-return]


class Underflow(Locator):
    __slots__ = ()
    NAME = "underflow"

    def __call__(self, axis: PlottableAxis) -> int:  # noqa: ARG002
        return -1 + self.offset


underflow = Underflow()


class Overflow(Locator):
    __slots__ = ()
    NAME = "overflow"

    def __call__(self, axis: PlottableAxis) -> int:
        return len(axis) + self.offset


overflow = Overflow()


class at:
    __slots__ = ("value",)

    def __init__(self, value: int) -> None:
        self.value = value

    def __call__(self, axis: PlottableAxis) -> int:  # noqa: ARG002
        return self.value


class rebin:
    """
    When used in the step of a Histogram's slice, rebin(n) combines bins,
    scaling their widths by a factor of n. If the number of bins is not
    divisible by n, the remainder is added to the overflow bin.
    """

    def __init__(self, factor: int) -> None:
        # Items with .factor are specially treated in boost-histogram,
        # performing a high performance rebinning
        self.factor = factor

    if typing.TYPE_CHECKING:
        # Type checkers think that this is required
        def __index__(self) -> int:
            return 42
