from __future__ import annotations

import dataclasses
from typing import Any

from uhi.io import remove_writer_info
from uhi.io._common import _convert_input


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
