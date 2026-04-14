from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import packaging.version
import pytest
from helpers import convert_histogram_to_32bit

import uhi.io.json
from uhi.io import to_sparse

h5py = pytest.importorskip("h5py", reason="h5py is not installed")
uhi_io_hdf5 = pytest.importorskip("uhi.io.hdf5")

BHVERSION = packaging.version.Version(importlib.metadata.version("boost_histogram"))
HISTVERSION = packaging.version.Version(importlib.metadata.version("hist"))


def test_valid_json(valid: Path, tmp_path: Path, sparse: bool) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    if sparse:
        hists = {name: to_sparse(hist) for name, hist in hists.items()}

    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        for name, hist in hists.items():
            uhi_io_hdf5.write(h5_file.create_group(name), hist)

    with h5py.File(tmp_file, "r") as h5_file:
        rehists = {name: uhi_io_hdf5.read(h5_file[name]) for name in hists}

    assert hists.keys() == rehists.keys()

    for name in hists:
        hist = hists[name]
        rehist = rehists[name]

        # Check that the JSON representation is the same
        data = json.dumps(hist, default=uhi.io.json.default, sort_keys=True)
        redata = json.dumps(rehist, default=uhi.io.json.default, sort_keys=True)

        redata = redata.replace(" ", "").replace("\n", "")
        data = data.replace(" ", "").replace("\n", "")

        assert redata == data


def test_reg_load(tmp_path: Path, resources: Path) -> None:
    data = resources / "valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        uhi_io_hdf5.write(
            h5_file.create_group("one"), hists["one"], min_compress_elements=0
        )

    with h5py.File(tmp_file, "r") as h5_file:
        one = uhi_io_hdf5.read(h5_file["one"])

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


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_bh(tmp_path: Path) -> None:
    import boost_histogram as bh

    h = bh.Histogram(
        bh.axis.Regular(3, 13, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        uhi_io_hdf5.write(h5_file.create_group("histogram"), h)

    with h5py.File(tmp_file, "r") as h5_file:
        rehist = uhi_io_hdf5.read(h5_file["histogram"])

    h2 = bh.Histogram(rehist)

    assert h == h2


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
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        uhi_io_hdf5.write(h5_file.create_group("histogram"), h)

    with h5py.File(tmp_file, "r") as h5_file:
        rehist = uhi_io_hdf5.read(h5_file["histogram"])
    h2 = hist.Hist(rehist)
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
def test_convert_bh_32bit_hdf5(tmp_path: Path, storage_type: str) -> None:
    """Test serialization of 32-bit histograms via HDF5."""
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

    # Write to HDF5
    tmp_file = tmp_path / "test_32bit.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        uhi_io_hdf5.write(h5_file.create_group("histogram"), uhi_32bit)

    # Read back from HDF5
    with h5py.File(tmp_file, "r") as h5_file:
        rehist_32bit = uhi_io_hdf5.read(h5_file["histogram"])

    # Verify storage type and data integrity
    assert rehist_32bit["storage"]["type"] == storage_type
    assert "values" in rehist_32bit["storage"]

    # Verify JSON representation is consistent
    redata = json.dumps(rehist_32bit, default=uhi.io.json.default, sort_keys=True)
    assert len(redata) > 0
