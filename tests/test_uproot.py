from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from helpers import convert_histogram_to_32bit, scalar_no_axis_storage
from pytest import approx

import uhi.io._files
import uhi.io.json
import uhi.io.ops
import uhi.schema
from uhi.io import ARRAY_KEYS, to_sparse

uproot = pytest.importorskip("uproot")
uhi_io_uproot = pytest.importorskip("uhi.io.uproot")


def _roundtrip(tmp_path: Path, hists: dict[str, Any]) -> dict[str, Any]:
    tmp_file = tmp_path / "test.root"
    with uproot.recreate(tmp_file) as root_file:
        for name, hist in hists.items():
            uhi_io_uproot.write(root_file, name, hist)

    with uproot.open(tmp_file) as root_file:
        return {name: uhi_io_uproot.read(root_file, name) for name in hists}


def test_valid_json(valid: Path, tmp_path: Path, sparse: bool) -> None:
    hists = uhi.io._files.load(valid)
    if sparse:
        hists = {name: to_sparse(hist) for name, hist in hists.items()}

    rehists = _roundtrip(tmp_path, hists)

    assert hists.keys() == rehists.keys()
    for name, hist in hists.items():
        scalar_no_axis_storage(hist)
        data = json.dumps(hist, default=uhi.io.json.default, sort_keys=True)
        redata = json.dumps(rehists[name], default=uhi.io.json.default, sort_keys=True)
        assert redata == data


def test_reg_load(tmp_path: Path, resources: Path) -> None:
    hists = uhi.io._files.load(resources / "valid/reg.json")
    rehists = _roundtrip(tmp_path, hists)

    # One single-entry RNTuple per histogram
    with uproot.open(tmp_path / "test.root") as root_file:
        ntuple = root_file["one"]
        assert set(ntuple.keys()) == {"uhi", "values"}
        assert ntuple.num_entries == 1
        native_one = json.loads(ntuple.arrays()["uhi"][0])
    assert native_one["storage"]["values"] == "values"

    one = rehists["one"]
    assert one["metadata"] == {"one": True, "two": 2, "three": "three"}
    assert one["axes"][0]["type"] == "regular"
    assert one["axes"][0]["bins"] == 3
    assert one["storage"]["type"] == "int"
    assert one["storage"]["values"] == approx([1, 2, 3, 4, 5])
    assert rehists["two"]["storage"]["values"] == approx([1, 2, 3, 4, 5, 6, 7])


@pytest.mark.parametrize("value", ["description", "values", "axis_0_edges"])
def test_metadata_array_keys(tmp_path: Path, value: str) -> None:
    metadata = dict.fromkeys(ARRAY_KEYS, value)
    writer_info = {"test": metadata}
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "metadata": metadata,
        "writer_info": writer_info,
        "axes": [
            {
                "type": "variable",
                "edges": np.array([0.0, 1.0, 2.0]),
                "underflow": False,
                "overflow": False,
                "circular": False,
                "metadata": metadata,
                "writer_info": writer_info,
            }
        ],
        "storage": {"type": "double", "values": np.array([1.0, 2.0])},
    }

    rehist = _roundtrip(tmp_path, {"histogram": hist})["histogram"]

    assert rehist["metadata"] == metadata
    assert rehist["writer_info"] == writer_info
    assert rehist["axes"][0]["metadata"] == metadata
    assert rehist["axes"][0]["edges"] == approx(hist["axes"][0]["edges"])
    assert rehist["storage"]["values"] == approx(hist["storage"]["values"])


def test_subdirectory(tmp_path: Path, resources: Path) -> None:
    hists = uhi.io._files.load(resources / "valid/2d.json")
    rehist = _roundtrip(tmp_path, {"sub/main": hists["main"]})["sub/main"]

    with uproot.open(tmp_path / "test.root") as root_file:
        assert root_file.classname_of("sub") == "TDirectory"
        rehist_sub = uhi_io_uproot.read(root_file["sub"], "main")

    for h in (rehist, rehist_sub):
        assert h["storage"]["values"] == approx(hists["main"]["storage"]["values"])


def test_0d_scalar_storage(tmp_path: Path) -> None:
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "axes": [],
        "storage": {
            "type": "weighted",
            "values": np.array(6.0),
            "variances": np.array(8.0),
        },
    }
    rehist = _roundtrip(tmp_path, {"h": hist})["h"]

    for key in ("values", "variances"):
        assert rehist["storage"][key].shape == ()
        assert rehist["storage"][key] == hist["storage"][key]


def test_unsupported_dtype(tmp_path: Path) -> None:
    hist: dict[str, Any] = {
        "uhi_schema": 1,
        "axes": [],
        "storage": {"type": "double", "values": np.array(1.0, dtype=np.float16)},
    }
    with (
        uproot.recreate(tmp_path / "test.root") as root_file,
        pytest.raises(TypeError, match="float16"),
    ):
        uhi_io_uproot.write(root_file, "h", hist)


@pytest.mark.parametrize("storage_type", ["int", "double", "weighted", "mean"])
def test_convert_bh_32bit(tmp_path: Path, storage_type: str) -> None:
    bh = pytest.importorskip("boost_histogram")

    axis = bh.axis.Regular(5, 0, 1, __dict__={"name": "x"})
    h: Any
    match storage_type:
        case "int":
            h = bh.Histogram(axis, storage=bh.storage.Int64())
            h.fill([0.1, 0.3, 0.3])
        case "double":
            h = bh.Histogram(axis, storage=bh.storage.Double())
            h.fill([0.1, 0.3, 0.5, 0.7, 0.9])
        case "weighted":
            h = bh.Histogram(axis, storage=bh.storage.Weight())
            h.fill([0.1, 0.3, 0.5], weight=[1.5, 2.5, 3.5])
        case _:
            h = bh.Histogram(axis, storage=bh.storage.Mean())
            h.fill([0.1, 0.3, 0.5], sample=[10.0, 20.0, 30.0])

    uhi_32bit = convert_histogram_to_32bit(h._to_uhi_())
    rehist = _roundtrip(tmp_path, {"h": uhi_32bit})["h"]

    storage: dict[str, Any] = dict(uhi_32bit["storage"])
    for key in ARRAY_KEYS & storage.keys():
        assert rehist["storage"][key].dtype == storage[key].dtype
        np.testing.assert_array_equal(rehist["storage"][key], storage[key])


def test_convert_hist(tmp_path: Path) -> None:
    hist = pytest.importorskip("hist")

    h = hist.Hist(
        hist.axis.Regular(10, 0, 1, name="a", label="A"),
        hist.axis.Integer(7, 13, overflow=False, name="b", label="B"),
        storage=hist.storage.Weight(),
        name="h",
        label="H",
    )
    h.fill(a=[0.1, 0.5], b=[8, 12])

    rehist = _roundtrip(tmp_path, {"histogram": h})["histogram"]
    assert hist.Hist(rehist) == h


# CLI


def test_cli_validate_path(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from uhi.__main__ import main

    hists = uhi.io._files.load(resources / "valid" / "reg.json")

    tmp_file = tmp_path / "test.root"
    with uproot.recreate(tmp_file) as root_file:
        for name, hist in hists.items():
            uhi_io_uproot.write(root_file, f"good/{name}", hist)
            broken = {**hist, "storage": {**hist["storage"], "type": "not_a_storage"}}
            uhi_io_uproot.write(root_file, f"bad/{name}", broken)

    assert set(uhi.schema.load(tmp_file, path="good")) == set(hists)
    assert set(uhi.schema.load(tmp_file, path="good/")) == set(hists)
    assert uhi.schema.load(tmp_file, path="good/one")["uhi_schema"] == 1

    main(["validate", f"{tmp_file}:good", f"{tmp_file}:good/one"])
    assert capsys.readouterr().out.count("OK") == 2

    with pytest.raises(SystemExit):
        main(["validate", str(tmp_file)])
    assert "ERROR" in capsys.readouterr().out

    with pytest.raises(SystemExit):
        main(["validate", f"{tmp_file}:missing"])
    assert capsys.readouterr().out.startswith("ERROR")


def test_load_non_rntuple(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from uhi.__main__ import main

    tmp_file = tmp_path / "test.root"
    with uproot.recreate(tmp_file) as root_file:
        root_file["th1"] = np.histogram([1, 2, 3])

    with pytest.raises(ValueError, match="not a histogram or directory"):
        uhi.io._files.load(tmp_file, path="th1")

    with pytest.raises(SystemExit):
        main(["validate", f"{tmp_file}:th1"])
    assert "not a histogram or directory" in capsys.readouterr().out


@pytest.mark.parametrize("out_suffix", [".root", ".json"])
def test_cli_add(resources: Path, tmp_path: Path, out_suffix: str) -> None:
    from uhi.__main__ import main

    hists = uhi.io._files.load(resources / "valid/reg.json")
    files = [tmp_path / "in1.root", tmp_path / "in2.root"]
    for file in files:
        with uproot.recreate(file) as root_file:
            for name, hist in hists.items():
                uhi_io_uproot.write(root_file, f"sub/{name}", hist)
    target = tmp_path / f"out{out_suffix}"

    main(["add", str(target), *map(str, files)])

    names = {f"sub/{name}" for name in hists}
    inputs = [uhi.io._files.load(file) for file in files]
    result = uhi.io._files.load(target)
    assert result.keys() == names
    for name in names:
        expected = uhi.io.ops.add(*(h[name] for h in inputs))
        assert result[name]["storage"]["values"] == approx(
            expected["storage"]["values"]
        )


def test_write_non_native_byte_order(tmp_path: Path) -> None:
    swapped = np.dtype("f8").newbyteorder()
    hist = {
        "uhi_schema": 1,
        "axes": [
            {
                "type": "regular",
                "lower": 0.0,
                "upper": 1.0,
                "bins": 2,
                "underflow": False,
                "overflow": False,
                "circular": False,
            }
        ],
        "storage": {"type": "double", "values": np.array([1.0, 2.0], dtype=swapped)},
    }
    rehist = _roundtrip(tmp_path, {"h": hist})["h"]
    assert rehist["storage"]["values"] == approx([1.0, 2.0])


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("5.7.0", True),
        ("5.7.0rc1", True),
        ("6.0.0", True),
        ("5.6.3", False),
        ("4.3.7", False),
    ],
)
def test_uproot_version_check(
    monkeypatch: pytest.MonkeyPatch, version: str, expected: bool
) -> None:
    monkeypatch.setattr("importlib.metadata.version", lambda _: version)
    uhi.io._files._uproot_available.cache_clear()
    assert uhi.io._files._uproot_available() is expected
    uhi.io._files._uproot_available.cache_clear()
