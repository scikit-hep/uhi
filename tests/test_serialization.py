from __future__ import annotations

import dataclasses
from typing import Any

from uhi.io import from_sparse, remove_writer_info, to_sparse
from uhi.io._common import _convert_input
from uhi.typing.serialization import AnyStorageIR


def test_remove_writer_info() -> None:
    d = {"uhi_schema": 1, "writer_info": {"a": {"foo": "bar"}, "b": {"FOO": "BAR"}}}

    assert remove_writer_info(d, library=None) == {"uhi_schema": 1}
    assert remove_writer_info(d, library="a") == {
        "uhi_schema": 1,
        "writer_info": {"b": {"FOO": "BAR"}},
    }
    assert remove_writer_info(d, library="b") == {
        "uhi_schema": 1,
        "writer_info": {"a": {"foo": "bar"}},
    }
    assert remove_writer_info(d, library="c") == d


@dataclasses.dataclass
class _Simple:
    value: dict[str, Any]

    def _to_uhi_(self) -> dict[str, Any]:
        return self.value


def test_remove_empty_metadata() -> None:
    d = {
        "uhi_schema": 1,
        "writer_info": {"boost-histogram": {"version": "1.6.1"}},
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": 1.0,
                "bins": 4,
                "underflow": True,
                "overflow": True,
                "circular": False,
                "metadata": {},
            }
        ],
        "storage": {
            "type": "weighted_mean",
            "sum_of_weights": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "sum_of_weights_squared": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "values": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "variances": [float("nan")] * 6,
        },
        "metadata": {},
    }

    h = _Simple(d)
    ir = _convert_input(h)

    assert "metadata" not in ir
    assert "metadata" not in ir["axes"][0]


def test_empty_storage_conversion() -> None:
    """Test that empty storages are handled correctly during conversion."""
    # Test each storage type with empty arrays
    storage_types: list[tuple[str, dict[str, Any]]] = [
        ("int", {}),
        ("double", {}),
        ("weighted", {}),
        ("mean", {}),
        ("weighted_mean", {}),
    ]

    for storage_type, arrays in storage_types:
        d = {
            "uhi_schema": 1,
            "axes": [
                {
                    "type": "regular",
                    "lower": 0.0,
                    "upper": 1.0,
                    "bins": 4,
                    "underflow": False,
                    "overflow": False,
                    "circular": False,
                }
            ],
            "storage": {"type": storage_type, **arrays},
        }

        h = _Simple(d)
        ir = _convert_input(h)

        storage: AnyStorageIR = ir["storage"]
        assert storage["type"] == storage_type
        # Verify no array fields are present
        array_keys = {
            "values",
            "variances",
            "counts",
            "sum_of_weights",
            "sum_of_weights_squared",
            "index",
        }
        assert not any(k in storage for k in array_keys)


def test_to_sparse_empty_storage() -> None:
    """Test that to_sparse leaves empty storages alone."""
    d = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": 1.0,
                "bins": 4,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
        ],
        "storage": {"type": "int"},
    }

    result = to_sparse(d)

    # Should return the same histogram unchanged
    assert result == d
    storage_result: AnyStorageIR = result["storage"]  # type: ignore[assignment]
    assert storage_result["type"] == "int"
    assert "values" not in storage_result


def test_from_sparse_empty_storage() -> None:
    """Test that from_sparse leaves empty storages alone."""
    d = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": 1.0,
                "bins": 4,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
        ],
        "storage": {"type": "double"},
    }

    result = from_sparse(d)

    # Should return the same histogram unchanged
    assert result == d
    storage_result: AnyStorageIR = result["storage"]  # type: ignore[assignment]
    assert storage_result["type"] == "double"
    assert "values" not in storage_result
