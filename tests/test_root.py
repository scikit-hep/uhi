from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import numpy as np
import packaging.version
import pytest
from helpers import convert_histogram_to_32bit
from pytest import approx

import uhi.io.json
import uhi.schema
from uhi.io import ARRAY_KEYS, to_sparse
from uhi.numpy_plottable import ensure_plottable_histogram

ROOT = pytest.importorskip("ROOT")
uhi_io_root = pytest.importorskip("uhi.io.root")

BHVERSION = packaging.version.Version(importlib.metadata.version("boost_histogram"))


def test_root_imported() -> None:
    assert ROOT.TString("hi") == "hi"


def test_root_th1f_convert() -> None:
    th = ROOT.TH1F("h1", "h1", 50, -2.5, 2.5)
    th.FillRandom("gaus", 10000)
    h = ensure_plottable_histogram(th)
    assert all(th.GetBinContent(i + 1) == approx(iv) for i, iv in enumerate(h.values()))
    var = h.variances()
    assert var is not None
    assert all(th.GetBinError(i + 1) == approx(ie) for i, ie in enumerate(np.sqrt(var)))


def test_root_th2f_convert() -> None:
    th = ROOT.TH2F("h2", "h2", 50, -2.5, 2.5, 50, -2.5, 2.5)
    _ = ROOT.TF2("xyg", "xygaus", -2.5, 2.5, -2.5, 2.5)
    th.FillRandom("xyg", 10000)
    h = ensure_plottable_histogram(th)
    assert all(
        th.GetBinContent(i + 1, j + 1) == approx(iv)
        for i, row in enumerate(h.values())
        for j, iv in enumerate(row)
    )
    var = h.variances()
    assert var is not None
    assert all(
        th.GetBinError(i + 1, j + 1) == approx(ie)
        for i, row in enumerate(np.sqrt(var))
        for j, ie in enumerate(row)
    )


# Serialization


def test_valid_json(valid: Path, tmp_path: Path, sparse: bool) -> None:
    data = valid.read_text(encoding="utf-8")
    hists = json.loads(data, object_hook=uhi.io.json.object_hook)
    if sparse:
        hists = {name: to_sparse(hist) for name, hist in hists.items()}

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        for name, hist in hists.items():
            uhi_io_root.write(root_file, name, hist)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehists = {name: uhi_io_root.read(root_file, name) for name in hists}

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

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        for name, hist in hists.items():
            uhi_io_root.write(root_file, name, hist)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehists = {name: uhi_io_root.read(root_file, name) for name in hists}

        # One single-entry RNTuple per histogram
        with ROOT.RNTupleReader.Open(root_file.Get("one")) as reader:
            fields = {
                field.GetFieldName()
                for field in reader.GetDescriptor().GetTopLevelFields()
            }
            assert fields == {"uhi", "values"}
            assert reader.GetNEntries() == 1
            entry = reader.CreateEntry()
            reader.LoadEntry(0, entry)
            native_one = json.loads(str(entry["uhi"]))

    assert native_one["storage"]["values"] == "values"

    one = rehists["one"]
    two = rehists["two"]

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

    assert two["storage"]["type"] == "double"
    assert two["storage"]["values"] == pytest.approx([1, 2, 3, 4, 5, 6, 7])


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

    tmp_file = tmp_path / "metadata.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "histogram", hist)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file, "histogram")

    assert rehist["metadata"] == metadata
    assert rehist["writer_info"] == writer_info
    assert rehist["axes"][0]["metadata"] == metadata
    assert rehist["axes"][0]["writer_info"] == writer_info
    assert rehist["axes"][0]["edges"] == pytest.approx(hist["axes"][0]["edges"])
    assert rehist["storage"]["values"] == pytest.approx(hist["storage"]["values"])


def test_two_variable_axes(tmp_path: Path) -> None:
    """Two variable axes must not collide on their field names."""
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
            "values": np.arange(6, dtype=np.float64).reshape(3, 2),
        },
    }

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "h", hist)

    # write() must not replace the caller's arrays with field names.
    assert isinstance(hist["axes"][0]["edges"], np.ndarray)
    assert isinstance(hist["storage"]["values"], np.ndarray)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file, "h")

    assert rehist["axes"][0]["edges"] == pytest.approx(edges_a)
    assert rehist["axes"][1]["edges"] == pytest.approx(edges_b)
    assert rehist["storage"]["values"].shape == (3, 2)
    assert rehist["storage"]["values"] == pytest.approx(hist["storage"]["values"])


def test_subdirectory(tmp_path: Path, resources: Path) -> None:
    data = resources / "valid/2d.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file.mkdir("sub"), "main", hists["main"])

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file.Get("sub"), "main")

    assert rehist["storage"]["values"] == pytest.approx(
        hists["main"]["storage"]["values"]
    )


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_bh(tmp_path: Path) -> None:
    import boost_histogram as bh

    h = bh.Histogram(
        bh.axis.Regular(3, 13, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "histogram", h)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file, "histogram")

    h2 = bh.Histogram(rehist)

    assert h == h2


@pytest.mark.skipif(
    packaging.version.Version("1.7.2") > BHVERSION,
    reason="Requires boost-histogram 1.7.2+ for keep_storage=False support",
)
def test_convert_bh_no_storage(tmp_path: Path) -> None:
    """Test ROOT serialization with keep_storage=False (structure-only histograms)."""
    import boost_histogram as bh
    import boost_histogram.serialization

    h = bh.Histogram(
        bh.axis.Regular(3, 0, 10, __dict__={"name": "x"}), storage=bh.storage.Weight()
    )
    h.fill([0.1, 0.3, 0.5], weight=[1.5, 2.5, 3.5])

    uhi_dict = boost_histogram.serialization.to_uhi(h, keep_storage=False)
    assert uhi_dict["storage"]["type"] == "weighted"
    assert "values" not in uhi_dict["storage"]

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "histogram", uhi_dict)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file, "histogram")

    h2 = bh.Histogram(rehist)
    assert h.axes == h2.axes
    assert isinstance(h2.storage_type(), bh.storage.Weight)


@pytest.mark.skipif(
    packaging.version.Version("1.6.1") > BHVERSION,
    reason="Requires boost-histogram 1.6+",
)
def test_convert_hist(tmp_path: Path) -> None:
    h: Any
    try:
        import hist

        h = hist.Hist(
            hist.axis.Regular(10, 0, 1, name="a", label="A"),
            hist.axis.Integer(7, 13, overflow=False, name="b", label="B"),
            storage=hist.storage.Weight(),
            name="h",
            label="H",
        )
    except ImportError:
        # Fall back to boost-histogram (as in the ROOT CI environment)
        import boost_histogram as bh

        h = bh.Histogram(
            bh.axis.Regular(10, 0, 1, __dict__={"name": "a", "label": "A"}),
            bh.axis.Integer(
                7, 13, overflow=False, __dict__={"name": "b", "label": "B"}
            ),
            storage=bh.storage.Weight(),
        )

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "histogram", h)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist = uhi_io_root.read(root_file, "histogram")
    h2 = type(h)(rehist)
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
def test_convert_bh_32bit_root(tmp_path: Path, storage_type: str) -> None:
    """Test serialization of 32-bit histograms via ROOT."""
    import boost_histogram as bh

    axis = bh.axis.Regular(5, 0, 1, __dict__={"name": "x"})
    h: Any

    if storage_type == "int":
        h = bh.Histogram(axis, storage=bh.storage.Int64())
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

    uhi_32bit = convert_histogram_to_32bit(h._to_uhi_())

    tmp_file = tmp_path / "test_32bit.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        uhi_io_root.write(root_file, "histogram", uhi_32bit)

    with ROOT.TFile.Open(str(tmp_file)) as root_file:
        rehist_32bit = uhi_io_root.read(root_file, "histogram")

    # The 32-bit dtypes are preserved by the field types
    assert rehist_32bit["storage"]["type"] == storage_type
    assert (
        rehist_32bit["storage"]["values"].dtype == uhi_32bit["storage"]["values"].dtype
    )
    assert rehist_32bit["storage"]["values"] == pytest.approx(
        uhi_32bit["storage"]["values"]
    )


# CLI


def test_cli_validate_root(
    valid: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from uhi.__main__ import main

    hists = json.loads(
        valid.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        # Nest one level to check that directories are searched recursively
        directory = root_file.mkdir("nested")
        for name, hist in hists.items():
            uhi_io_root.write(directory, name, hist)

    main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("OK")


def test_cli_validate_root_invalid(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from uhi.__main__ import main

    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        for name, hist in hists.items():
            hist = dict(hist)  # noqa: PLW2901
            hist["storage"] = {**hist["storage"], "type": "not_a_storage"}
            uhi_io_root.write(root_file, name, hist)

    with pytest.raises(SystemExit):
        main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_validate_root_path(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from uhi.__main__ import main

    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )

    tmp_file = tmp_path / "test.root"
    with ROOT.TFile.Open(str(tmp_file), "RECREATE") as root_file:
        good = root_file.mkdir("good")
        bad = root_file.mkdir("bad")
        for name, hist in hists.items():
            uhi_io_root.write(good, name, hist)
            broken = {**hist, "storage": {**hist["storage"], "type": "not_a_storage"}}
            uhi_io_root.write(bad, name, broken)

    assert set(uhi.schema.load(tmp_file, path="good")) == set(hists)
    assert set(uhi.schema.load(tmp_file, path="good/")) == set(hists)
    single = uhi.schema.load(tmp_file, path="good/one")
    assert single["uhi_schema"] == 1

    main(["validate", f"{tmp_file}:good", f"{tmp_file}:good/one"])
    assert capsys.readouterr().out.count("OK") == 2

    with pytest.raises(SystemExit):
        main(["validate", f"{tmp_file}:bad"])
    assert capsys.readouterr().out.startswith("ERROR")

    with pytest.raises(SystemExit):
        main(["validate", f"{tmp_file}:missing"])
    assert capsys.readouterr().out.startswith("ERROR")
