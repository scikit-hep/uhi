from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import numpy as np
import packaging.version
import pytest

import uhi.io.json
from uhi.io import to_sparse

zarr = pytest.importorskip("zarr", reason="zarr is not installed")
uhi_io_zarr = pytest.importorskip("uhi.io.zarr")

BHVERSION = packaging.version.Version(importlib.metadata.version("boost_histogram"))


def test_valid_json(valid: Path, tmp_path: Path, sparse: bool) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    if sparse:
        hists = {name: to_sparse(hist) for name, hist in hists.items()}

    tmp_file = tmp_path / "test.zarr"
    zarr_file = zarr.open_group(tmp_file, mode="w")
    for name, hist in hists.items():
        uhi_io_zarr.write(zarr_file.create_group(name), hist)

    zarr_file = zarr.open_group(tmp_file, mode="r")
    rehists = {name: uhi_io_zarr.read(zarr_file[name]) for name in hists}

    assert hists.keys() == rehists.keys()

    for name in hists:
        data = json.dumps(hists[name], default=uhi.io.json.default, sort_keys=True)
        redata = json.dumps(rehists[name], default=uhi.io.json.default, sort_keys=True)
        assert redata == data


def test_reg_load(tmp_path: Path, resources: Path) -> None:
    data = resources / "valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), hists["one"])
    one = uhi_io_zarr.read(zarr.open_group(tmp_file, mode="r"))

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


def test_writer_info(tmp_path: Path) -> None:
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "writer_info": {"boost-histogram": {"version": "1.0.0"}},
        "axes": [
            {
                "type": "category_str",
                "categories": ["a", "bb"],
                "flow": False,
                "writer_info": {"boost-histogram": {"growth": True}},
            }
        ],
        "storage": {"type": "int", "values": np.array([1, 2])},
    }

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), hist)
    rehist = uhi_io_zarr.read(zarr.open_group(tmp_file, mode="r"))

    assert rehist["writer_info"] == {"boost-histogram": {"version": "1.0.0"}}
    assert rehist["axes"][0]["writer_info"] == {"boost-histogram": {"growth": True}}
    assert rehist["axes"][0]["categories"] == ["a", "bb"]


def test_single_chunk(tmp_path: Path) -> None:
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": 1.0,
                "bins": 100_000,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
        ],
        "storage": {"type": "double", "values": np.ones(100_000)},
    }

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), hist)

    values = zarr.open_group(tmp_file, mode="r")["storage/values"]
    assert values.chunks == (100_000,)


def test_scalar_storage(tmp_path: Path) -> None:
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "axes": [],
        "storage": {"type": "double", "values": 3.0},
    }

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), hist)
    rehist = uhi_io_zarr.read(zarr.open_group(tmp_file, mode="r"))

    assert rehist["axes"] == []
    assert rehist["storage"]["values"] == pytest.approx(3.0)


def test_axis_order_many_axes(tmp_path: Path) -> None:
    n_axes = 12
    uppers = [float(i + 1) for i in range(n_axes)]
    hist = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": upper,
                "bins": 1,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
            for upper in uppers
        ],
        "storage": {"type": "double", "values": np.ones((1,) * n_axes)},
    }

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), hist)
    rehist = uhi_io_zarr.read(zarr.open_group(tmp_file, mode="r"))

    assert [ax["upper"] for ax in rehist["axes"]] == pytest.approx(uppers)


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_bh(tmp_path: Path) -> None:
    import boost_histogram as bh

    h = bh.Histogram(
        bh.axis.Regular(3, 13, 10, __dict__={"name": "x"}),
        bh.axis.StrCategory(["a", "b"]),
        storage=bh.storage.Weight(),
    )
    h.fill([11, 12], ["a", "b"], weight=[1.5, 2.5])

    tmp_file = tmp_path / "test.zarr"
    uhi_io_zarr.write(zarr.open_group(tmp_file, mode="w"), h)
    rehist = uhi_io_zarr.read(zarr.open_group(tmp_file, mode="r"))

    assert h == bh.Histogram(rehist)
