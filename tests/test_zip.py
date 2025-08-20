from __future__ import annotations

import copy
import importlib.metadata
import json
import zipfile
from pathlib import Path

import packaging.version
import pytest

import uhi.io.json
import uhi.io.zip
from uhi.io import to_sparse

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
            uhi.io.zip.write(zip_file, name, copy.deepcopy(hist))
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehists = {name: uhi.io.zip.read(zip_file, name) for name in hists}

    assert hists.keys() == rehists.keys()

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
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        uhi.io.zip.write(zip_file, "histogram", h)
    with zipfile.ZipFile(tmp_file, "r") as zip_file:
        rehist = uhi.io.zip.read(zip_file, "histogram")
    h2 = hist.Hist(rehist)
    assert h == h2
