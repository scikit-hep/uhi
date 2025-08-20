from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import packaging.version
import pytest

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
