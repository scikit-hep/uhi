from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import packaging.version
import pytest

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
