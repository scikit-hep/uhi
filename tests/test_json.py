from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import packaging.version
import pytest
from helpers import convert_histogram_to_32bit

import uhi.io.json

BHVERSION = packaging.version.Version(importlib.metadata.version("boost_histogram"))
HISTVERSION = packaging.version.Version(importlib.metadata.version("hist"))


def test_valid_json(valid: Path) -> None:
    data = valid.read_text(encoding="utf-8")
    hist = json.loads(data, object_hook=uhi.io.json.object_hook)
    redata = json.dumps(hist, default=uhi.io.json.default)

    rehist = json.loads(redata, object_hook=uhi.io.json.object_hook)
    assert redata.replace(" ", "").replace("\n", "") == data.replace(" ", "").replace(
        "\n", ""
    )

    assert hist.keys() == rehist.keys()


def test_reg_load(resources: Path) -> None:
    data = resources / "valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )
    one = hists["one"]
    two = hists["two"]

    assert one["metadata"] == {"one": True, "two": 2, "three": "three"}

    assert len(one["axes"]) == 1
    assert one["axes"][0]["type"] == "regular"
    assert one["axes"][0]["lower"] == pytest.approx(0)
    assert one["axes"][0]["upper"] == pytest.approx(5)
    assert one["axes"][0]["bins"] == 3
    assert one["axes"][0]["underflow"]
    assert one["axes"][0]["overflow"]
    assert not one["axes"][0]["circular"]

    assert one["storage"]["type"] == "int"
    assert one["storage"]["values"] == pytest.approx([1, 2, 3, 4, 5])

    assert len(two["axes"]) == 1
    assert two["axes"][0]["type"] == "regular"
    assert two["axes"][0]["lower"] == pytest.approx(0)
    assert two["axes"][0]["upper"] == pytest.approx(5)
    assert two["axes"][0]["bins"] == 5
    assert two["axes"][0]["underflow"]
    assert two["axes"][0]["overflow"]
    assert not two["axes"][0]["circular"]

    assert two["storage"]["type"] == "double"
    assert two["storage"]["values"] == pytest.approx([1, 2, 3, 4, 5, 6, 7])


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_bh() -> None:
    import boost_histogram as bh

    h = bh.Histogram(
        bh.axis.Regular(3, 13, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    redata = json.dumps(h, default=uhi.io.json.default)
    rehist = json.loads(redata, object_hook=uhi.io.json.object_hook)
    h2 = bh.Histogram(rehist)

    assert h == h2


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION
    or packaging.version.Version("2.9.0") > HISTVERSION,
    reason="Requires boost-histogram 1.6+ / Hist 2.9+",
)
def test_convert_hist() -> None:
    import hist

    h = hist.Hist(
        hist.axis.Regular(10, 0, 1, name="a", label="A"),
        hist.axis.Integer(7, 13, overflow=False, name="b", label="B"),
        storage=hist.storage.Weight(),
        name="h",
        label="H",
    )
    redata = json.dumps(h, default=uhi.io.json.default)
    rehist = json.loads(redata, object_hook=uhi.io.json.object_hook)
    h2 = hist.Hist(rehist)
    assert h == h2


def test_empty_storage_roundtrip() -> None:
    """Test that empty storages can be read and written with JSON."""
    data = {
        "empty_int": {
            "uhi_schema": 1,
            "axes": [
                {
                    "type": "regular",
                    "lower": 0,
                    "upper": 10,
                    "bins": 5,
                    "underflow": False,
                    "overflow": False,
                    "circular": False,
                }
            ],
            "storage": {"type": "int"},
        }
    }

    # Dump to JSON
    json_str = json.dumps(data, default=uhi.io.json.default)

    # Load back from JSON
    loaded = json.loads(json_str, object_hook=uhi.io.json.object_hook)

    # Verify structure is preserved
    assert loaded == data
    assert loaded["empty_int"]["storage"]["type"] == "int"
    assert "values" not in loaded["empty_int"]["storage"]


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
@pytest.mark.parametrize(
    "storage_type",
    [
        pytest.param("int", id="int_storage"),
        pytest.param("double", id="double_storage"),
        pytest.param("weighted", id="weighted_storage"),
        pytest.param("mean", id="mean_storage"),
    ],
)
def test_convert_bh_32bit(storage_type: str) -> None:
    """Test serialization of 32-bit histograms via JSON."""
    import boost_histogram as bh

    # Create histogram with appropriate storage type
    axis = bh.axis.Regular(5, 0, 1, __dict__={"name": "x"})
    h: bh.Histogram[Any]

    if storage_type == "int":
        h = bh.Histogram(axis, storage=bh.storage.Int64())
        # Fill with some data
        for i in range(5):
            h.fill([0.1 + i * 0.15] * 10)
    elif storage_type == "double":
        h = bh.Histogram(axis, storage=bh.storage.Double())
        h.fill([0.1, 0.3, 0.5, 0.7, 0.9])
    elif storage_type == "weighted":
        h = bh.Histogram(axis, storage=bh.storage.Weight())
        h.fill([0.1, 0.3, 0.5], weight=[1.5, 2.5, 3.5])
    elif storage_type == "mean":
        h = bh.Histogram(axis, storage=bh.storage.Mean())
        h.fill([0.1, 0.3, 0.5], sample=[10.0, 20.0, 30.0])
    else:
        msg = f"Unknown storage type: {storage_type}"
        raise ValueError(msg)

    # Convert to UHI format
    uhi_dict = h._to_uhi_()

    # Convert to 32-bit
    uhi_32bit = convert_histogram_to_32bit(uhi_dict)

    # Serialize via JSON
    redata = json.dumps(uhi_32bit, default=uhi.io.json.default)

    # Deserialize
    rehist_32bit = json.loads(redata, object_hook=uhi.io.json.object_hook)

    # Verify storage type and data integrity
    assert rehist_32bit["storage"]["type"] == storage_type
    assert "values" in rehist_32bit["storage"]

    # Verify values can be serialized again without error
    redata2 = json.dumps(rehist_32bit, default=uhi.io.json.default)
    assert len(redata2) > 0
