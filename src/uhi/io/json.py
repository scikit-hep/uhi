from __future__ import annotations

from typing import Any

import numpy as np

from . import ARRAY_KEYS
from ._common import _convert_input

__all__ = ["default", "object_hook"]


def __dir__() -> list[str]:
    return __all__


def default(obj: Any, /) -> Any:
    if hasattr(obj, "_to_uhi_"):
        return _convert_input(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert ndarray to list
    msg = f"Object of type {type(obj)} is not JSON serializable"
    raise TypeError(msg)


def object_hook(dct: dict[str, Any], /) -> dict[str, Any]:
    """
    Decode a histogram from a dictionary.
    """
    for item in ARRAY_KEYS & dct.keys():
        if isinstance(dct[item], list):
            dct[item] = np.asarray(dct[item])

    return dct
