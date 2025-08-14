from __future__ import annotations

import copy
from typing import Any, TypeVar

__all__ = ["ARRAY_KEYS", "LIST_KEYS", "remove_writer_info"]

ARRAY_KEYS = frozenset(
    [
        "values",
        "variances",
        "edges",
        "counts",
        "sum_of_weights",
        "sum_of_weights_squared",
    ]
)

LIST_KEYS = frozenset(
    [
        "categories",
    ]
)

T = TypeVar("T", bound="dict[str, Any]")


def remove_writer_info(obj: T, /, *, library: str | None) -> T:
    """
    Removes all ``writer_info`` for a library from a histogram dict, axes dict,
    or storage dict. Makes copies where required, and the outer dictionary is
    always copied.

    Specify a library name, or ``None`` to remove all.
    """

    obj = copy.copy(obj)
    if library is None:
        obj.pop("writer_info")
    elif library in obj.get("writer_info", {}):
        obj["writer_info"] = copy.copy(obj["writer_info"])
        del obj["writer_info"][library]

    if "axes" in obj:
        obj["axes"] = [remove_writer_info(ax, library=library) for ax in obj["axes"]]
    if "storage" in obj:
        obj["storage"] = remove_writer_info(obj["storage"], library=library)

    return obj
