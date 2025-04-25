from __future__ import annotations

__all__ = ["ARRAY_KEYS", "LIST_KEYS"]

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
