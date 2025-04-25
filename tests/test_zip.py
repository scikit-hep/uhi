from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path

import pytest

import uhi.io.json
import uhi.io.zip

DIR = Path(__file__).parent.resolve()

VALID_FILES = DIR.glob("resources/valid/*.json")


@pytest.mark.parametrize("filename", VALID_FILES, ids=lambda p: p.name)
def test_valid_json(filename: Path, tmp_path: Path) -> None:
    data = filename.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)

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


def test_reg_load(tmp_path: Path) -> None:
    data = DIR / "resources/valid/reg.json"
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
