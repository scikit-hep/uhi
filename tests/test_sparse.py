from __future__ import annotations

import json
from pathlib import Path

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
        assert np.allclose(dense["storage"][key], value)  # type: ignore[literal-required]


def test_all_valid(valid: Path) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    hists = {
        k: from_sparse(v) if "index" in v.get("storage", {}) else v
        for k, v in hists.items()
    }
    shists = {k: to_sparse(v) for k, v in hists.items()}
    for h in shists.values():
        if h["axes"]:
            assert "index" in h["storage"]
    dhists = {k: from_sparse(v) for k, v in shists.items()}
    for h in dhists.values():
        assert "index" not in h["storage"]

    assert hists.keys() == dhists.keys()
    for v, dv in zip(hists.values(), dhists.values()):
        assert v.keys() == dv.keys()
        assert v["axes"] == dv["axes"]
        assert v["storage"].keys() == dv["storage"].keys()
        assert v["storage"]["values"] == pytest.approx(dv["storage"]["values"])
        if v["storage"]["type"] == "weighted_mean":
            v_var = v["storage"]["variances"]
            dv_var = dv["storage"]["variances"]
            assert np.all(np.isnan(v_var) == np.isnan(dv_var))
            assert v_var[~np.isnan(v_var)] == pytest.approx(dv_var[~np.isnan(dv_var)])
            assert v["storage"]["sum_of_weights"] == pytest.approx(
                dv["storage"]["sum_of_weights"]
            )
            assert v["storage"]["sum_of_weights_squared"] == pytest.approx(
                dv["storage"]["sum_of_weights_squared"]
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
