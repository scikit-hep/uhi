from __future__ import annotations

import json
from pathlib import Path

import pytest

import uhi.io.json

zarr = pytest.importorskip("zarr", reason="zarr is not installed")
uhi_io_zarr = pytest.importorskip("uhi.io.zarr")

DIR = Path(__file__).parent.resolve()

VALID_FILES = DIR.glob("resources/valid/*.json")


@pytest.mark.parametrize("filename", VALID_FILES, ids=lambda p: p.name)
def test_valid_json(filename: Path, tmp_path: Path) -> None:
    data = filename.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)

    tmp_file = tmp_path / "test.zarr"

    zarr_file = zarr.open(tmp_file, mode="w")
    for name, hist in hists.items():
        uhi_io_zarr.write(zarr_file.create_group(name), hist)

    zarr_file = zarr.open(tmp_file, mode="r")
    rehists = {name: uhi_io_zarr.read(zarr_file[name]) for name in hists}

    assert hists.keys() == rehists.keys()

    for name in hists:
        hist = hists[name]
        rehist = rehists[name]

        # this is metadata, which is we can't compare against
        hist.pop("writer_info", None)

        # Check that the JSON representation is the same
        data = json.dumps(hist, default=uhi.io.json.default, sort_keys=True)
        redata = json.dumps(rehist, default=uhi.io.json.default, sort_keys=True)
        
        assert redata.replace(" ", "").replace("\n", "") == data.replace(
            " ", ""
        ).replace("\n", "")


def test_reg_load(tmp_path: Path) -> None:
    data = DIR / "resources/valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.zarr"
    zarr_file = zarr.open(tmp_file, mode="w")
    uhi_io_zarr.write(zarr_file.create_group("one"), hists["one"])

    zarr_file = zarr.open(tmp_file, mode="r")
    one = uhi_io_zarr.read(zarr_file["one"])

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
