from __future__ import annotations

import pytest

from uhi.tag import loc, overflow, rebin, underflow


def test_locator_offset_arithmetic() -> None:
    assert (loc(1.0) + 2).offset == 2
    assert (loc(1.0) - 2).offset == -2
    assert (overflow + 1).offset == 1
    assert (underflow - 1).offset == -1


@pytest.mark.parametrize("offset", [0.5, 1.0, "1"])
def test_locator_offset_must_be_int(offset: object) -> None:
    with pytest.raises(TypeError):
        loc(0.5, offset)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        loc(0.5) + offset  # type: ignore[operator]
    with pytest.raises(TypeError):
        loc(0.5) - offset  # type: ignore[operator]
    with pytest.raises(TypeError):
        overflow + offset  # type: ignore[operator]


def test_rebin() -> None:
    assert rebin(1).factor == 1
    assert rebin(3).factor == 3


def test_rebin_factor_must_be_int() -> None:
    with pytest.raises(TypeError):
        rebin(2.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("factor", [0, -1, -2])
def test_rebin_factor_must_be_positive(factor: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        rebin(factor)
