from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import uhi.io.json
from uhi.io import from_sparse, to_sparse
from uhi.typing.serialization import HistogramIR, WeightedStorageIR


def test_to_from_sparse_roundtrip() -> None:
    # Original dense data
    hist: HistogramIR = {
        "uhi_schema": 1,
        "storage": {
            "type": "weighted",
            "values": np.array([[0, 1, 0], [0, 2, 0]], dtype=float),
            "variances": np.array([[0, 0.1, 0], [0, 0, 0]], dtype=float),
        },
        "axes": [
            {"type": "boolean"},
            {
                "type": "regular",
                "bins": 3,
                "overflow": False,
                "underflow": False,
                "lower": 0,
                "upper": 1,
                "circular": False,
            },
        ],
    }

    # Convert to sparse
    shist = to_sparse(hist)
    sparse: WeightedStorageIR = shist["storage"]  # type: ignore[assignment]

    # Basic checks on sparse structure
    assert "index" in sparse
    index = sparse["index"]
    assert index.shape[0] == 2
    assert index.shape[1] == 2
    # Verify sparse arrays align with mask
    assert np.all(sparse["values"] == np.array([1.0, 2.0]))
    assert np.all(sparse["variances"] == np.array([0.1, 0.0]))

    # Convert back to dense
    dense = from_sparse(shist)

    # Check round-trip reconstruction
    for key, value in hist["storage"].items():
        if key == "type":
            continue
        assert np.allclose(dense["storage"][key], value)  # type: ignore[literal-required,arg-type]


def test_all_valid(valid: Path) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    hists = {
        k: from_sparse(v) if "index" in v.get("storage", {}) else v
        for k, v in hists.items()
    }
    shists = {k: to_sparse(v) for k, v in hists.items()}
    for h in shists.values():
        # Empty storages (metadata-only) won't get an index since there's no data
        has_data = len(h["storage"]) > 1  # More than just "type"
        if h["axes"] and has_data:
            assert "index" in h["storage"]
    dhists = {k: from_sparse(v) for k, v in shists.items()}
    for h in dhists.values():
        assert "index" not in h["storage"]

    assert hists.keys() == dhists.keys()
    for v, dv in zip(hists.values(), dhists.values(), strict=True):
        assert v.keys() == dv.keys()
        assert v["axes"] == dv["axes"]
        assert v["storage"].keys() == dv["storage"].keys()
        # Empty storages won't have values to compare
        if "values" in v["storage"] and "values" in dv["storage"]:
            assert v["storage"]["values"] == pytest.approx(dv["storage"]["values"])
        if v["storage"]["type"] == "weighted_mean":
            v_var = v["storage"].get("variances")
            dv_var = dv["storage"].get("variances")
            if v_var is not None and dv_var is not None:
                assert np.all(np.isnan(v_var) == np.isnan(dv_var))
                assert v_var[~np.isnan(v_var)] == pytest.approx(
                    dv_var[~np.isnan(dv_var)]
                )
            assert v["storage"].get("sum_of_weights") == pytest.approx(
                dv["storage"].get("sum_of_weights")
            )
            assert v["storage"].get("sum_of_weights_squared") == pytest.approx(
                dv["storage"].get("sum_of_weights_squared")
            )

        else:
            assert v["storage"].get("variances") == pytest.approx(
                dv["storage"].get("variances")
            )
            assert v["storage"].get("counts") == pytest.approx(
                dv["storage"].get("counts")
            )


@pytest.mark.parametrize("name", ["mean", "weighted_mean"])
def test_mean(resources: Path, name: str) -> None:
    data = resources.joinpath("valid/mean.json").read_text()
    hist = json.loads(data, object_hook=uhi.io.json.object_hook)[name]
    sparse_hist = to_sparse(hist)

    assert len(sparse_hist["storage"]["values"]) == 2
    assert sparse_hist["storage"]["index"].shape == (1, 2)


def test_from_sparse_empty_index_json_roundtrip() -> None:
    """An all-zero histogram has an empty index; JSON reads it back as float."""
    hist: HistogramIR = {
        "uhi_schema": 1,
        "storage": {"type": "double", "values": np.zeros(3)},
        "axes": [
            {
                "type": "regular",
                "bins": 3,
                "overflow": False,
                "underflow": False,
                "lower": 0,
                "upper": 1,
                "circular": False,
            },
        ],
    }
    text = json.dumps(to_sparse(hist), default=uhi.io.json.default)
    shist = json.loads(text, object_hook=uhi.io.json.object_hook)
    assert shist["storage"]["index"].shape == (1, 0)

    dense = from_sparse(shist)
    np.testing.assert_array_equal(dense["storage"]["values"], np.zeros(3))


def test_from_sparse_weighted_mean_int_variances() -> None:
    hist = json.loads(
        """{
        "uhi_schema": 1,
        "axes": [{"type": "regular", "lower": 0, "upper": 1, "bins": 2,
                  "underflow": false, "overflow": false, "circular": false}],
        "storage": {"type": "weighted_mean", "index": [[1]],
                    "sum_of_weights": [1], "sum_of_weights_squared": [1],
                    "values": [1], "variances": [1]}
        }""",
        object_hook=uhi.io.json.object_hook,
    )
    dense = from_sparse(hist)
    np.testing.assert_array_equal(dense["storage"]["variances"], [np.nan, 1.0])
    np.testing.assert_array_equal(dense["storage"]["values"], [0, 1])


@pytest.mark.parametrize(
    ("storage_type", "dtype"), [("int", np.int64), ("double", np.float64)]
)
def test_from_sparse_empty_json_dtype(storage_type: str, dtype: type) -> None:
    hist = json.loads(
        f"""{{
        "uhi_schema": 1,
        "axes": [{{"type": "regular", "lower": 0, "upper": 1, "bins": 2,
                  "underflow": false, "overflow": false, "circular": false}}],
        "storage": {{"type": "{storage_type}", "index": [[]], "values": []}}
        }}""",
        object_hook=uhi.io.json.object_hook,
    )
    values = from_sparse(hist)["storage"]["values"]
    assert values.dtype == dtype
    np.testing.assert_array_equal(values, [0, 0])


@pytest.mark.parametrize(
    ("storage_type", "dtype"),
    [("int", np.uint64), ("int", np.int32), ("double", np.float32)],
)
def test_from_sparse_empty_keeps_dtype(storage_type: str, dtype: type) -> None:
    hist: Any = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0,
                "upper": 1,
                "bins": 2,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
        ],
        "storage": {"type": storage_type, "values": np.zeros(2, dtype=dtype)},
    }
    values = from_sparse(to_sparse(hist))["storage"]["values"]
    assert values.dtype == dtype


def test_from_sparse_unknown_axis() -> None:
    hist: Any = {
        "uhi_schema": 1,
        "axes": [{"type": "integer"}],
        "storage": {"type": "int", "index": [[0]], "values": [3]},
    }
    with pytest.raises(ValueError, match="Unknown axis type 'integer'"):
        from_sparse(hist)
