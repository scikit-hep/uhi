from __future__ import annotations

import importlib.metadata
import json
import typing
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import packaging.version
import pytest
from helpers import convert_histogram_to_32bit

import uhi.io.json
import uhi.io.zip
from uhi.io import ARRAY_KEYS, to_sparse
from uhi.typing.serialization import AnyHistogramIR

BHVERSION = packaging.version.Version(importlib.metadata.version("boost_histogram"))
HISTVERSION = packaging.version.Version(importlib.metadata.version("hist"))


def test_valid_json(valid: Path, tmp_path: Path, sparse: bool) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    if sparse:
        hists = {name: to_sparse(hist) for name, hist in hists.items()}

    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        for name, hist in hists.items():
            # No deepcopy: write() must not mutate the caller's histogram.
            uhi.io.zip.write(zip_file, name, hist)
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehists = {name: uhi.io.zip.read(zip_file, name) for name in hists}

    assert hists.keys() == rehists.keys()

    # write() must not replace the caller's arrays with path strings.
    for hist in hists.values():
        for key in ARRAY_KEYS & hist["storage"].keys():
            assert not isinstance(hist["storage"][key], str)
        for axis in hist["axes"]:
            for key in ARRAY_KEYS & axis.keys():
                assert not isinstance(axis[key], str)

    for name in hists:
        hist = hists[name]
        rehist = rehists[name]

        # Check that the JSON representation is the same
        redata = json.dumps(hist, default=uhi.io.json.default)
        data = json.dumps(rehist, default=uhi.io.json.default)
        assert redata.replace(" ", "").replace("\n", "") == data.replace(
            " ", ""
        ).replace("\n", "")


def test_reg_load(tmp_path: Path, resources: Path) -> None:
    data = resources / "valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        for name, hist in hists.items():
            uhi.io.zip.write(zip_file, name, hist)
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        names = zip_file.namelist()
        rehists = {
            name[:-5]: uhi.io.zip.read(zip_file, name[:-5])
            for name in names
            if name.endswith(".json")
        }
        with zip_file.open("one.json") as f:
            native_one = json.load(f)

    assert set(names) == {
        "one_storage_values.npy",
        "one.json",
        "two_storage_values.npy",
        "two.json",
    }

    assert native_one["storage"]["values"] == "one_storage_values.npy"

    one = rehists["one"]
    two = rehists["two"]

    assert one.get("metadata", {}) == {"one": True, "two": 2, "three": "three"}

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


def test_two_variable_axes(tmp_path: Path) -> None:
    """Two variable axes must not collide on their zip filenames (issue #241)."""
    edges_a = np.array([0.0, 1.0, 2.0, 3.0])
    edges_b = np.array([0.0, 10.0, 20.0])

    def axis(edges: np.ndarray) -> dict[str, Any]:
        return {
            "type": "variable",
            "edges": edges,
            "underflow": False,
            "overflow": False,
            "circular": False,
        }

    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "axes": [axis(edges_a), axis(edges_b)],
        "storage": {
            "type": "double",
            "values": np.zeros((len(edges_a) - 1, len(edges_b) - 1)),
        },
    }

    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "h", typing.cast(AnyHistogramIR, hist))
        names = zip_file.namelist()

    # Distinct filenames per axis (no duplicate-name UserWarning, no overwrite).
    edge_names = [n for n in names if "_axis_" in n]
    assert len(edge_names) == 2
    assert len(set(edge_names)) == 2

    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist = uhi.io.zip.read(zip_file, "h")

    # Each axis must round-trip with its own edges, not the other axis's.
    assert rehist["axes"][0]["edges"] == pytest.approx(edges_a)
    assert rehist["axes"][1]["edges"] == pytest.approx(edges_b)


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_bh(tmp_path: Path) -> None:
    import boost_histogram as bh

    h = bh.Histogram(
        bh.axis.Regular(3, 13, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "histogram", h)
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist = uhi.io.zip.read(zip_file, "histogram")
    h2 = bh.Histogram[bh.storage.Weight](rehist)

    assert h == h2


@pytest.mark.skipif(
    packaging.version.Version("1.7.2") > BHVERSION,
    reason="Requires boost-histogram 1.7.2+ for keep_storage=False support",
)
def test_convert_bh_no_storage(tmp_path: Path) -> None:
    """Test ZIP serialization with keep_storage=False (structure-only histograms)."""
    import typing

    import boost_histogram as bh
    import boost_histogram.serialization

    from uhi.typing.serialization import AnyHistogramIR

    h = bh.Histogram(
        bh.axis.Regular(3, 0, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    h.fill([0.1, 0.3, 0.5], weight=[1.5, 2.5, 3.5])

    # Convert to UHI format without storage values
    uhi_untyped = boost_histogram.serialization.to_uhi(h, keep_storage=False)
    uhi_dict = typing.cast(AnyHistogramIR, uhi_untyped)

    # Verify storage has type but no values
    assert "storage" in uhi_dict
    assert uhi_dict["storage"]["type"] == "weighted"
    assert "values" not in uhi_dict["storage"]

    # Write to ZIP
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "histogram", uhi_dict)

    # Read back from ZIP
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist = uhi.io.zip.read(zip_file, "histogram")

    # Should be able to reconstruct a histogram with the same structure
    h2: bh.Histogram[bh.storage.Weight] = bh.Histogram(rehist)
    assert h.axes == h2.axes
    assert isinstance(h2.storage_type(), bh.storage.Weight)


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION
    or packaging.version.Version("2.9.0") > HISTVERSION,
    reason="Requires boost-histogram 1.6+ / Hist 2.9+",
)
def test_convert_hist(tmp_path: Path) -> None:
    import hist

    h = hist.Hist(
        hist.axis.Regular(10, 0, 1, name="a", label="A"),
        hist.axis.Integer(7, 13, overflow=False, name="b", label="B"),
        storage=hist.storage.Weight(),
        name="h",
        label="H",
    )
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "histogram", h)
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist = uhi.io.zip.read(zip_file, "histogram")
    h2 = hist.Hist[hist.storage.Double](rehist)
    assert h == h2


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
def test_convert_bh_32bit_zip(tmp_path: Path, storage_type: str) -> None:
    """Test serialization of 32-bit histograms via ZIP."""
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

    # Write to ZIP
    tmp_file = tmp_path / "test_32bit.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "histogram", uhi_32bit)

    # Read back from ZIP
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist_32bit = uhi.io.zip.read(zip_file, "histogram")

    # Verify storage type and data integrity
    assert rehist_32bit["storage"]["type"] == storage_type
    assert "values" in rehist_32bit["storage"]

    # Verify JSON representation is consistent
    redata = json.dumps(rehist_32bit, default=uhi.io.json.default)
    assert len(redata) > 0
