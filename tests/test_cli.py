from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import fastjsonschema
import pytest

import uhi.io._files
import uhi.io.json
import uhi.io.zip
import uhi.schema
from uhi.__main__ import main


def test_cli_validate(resources: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate", str(resources / "valid" / "reg.json")])
    assert capsys.readouterr().out.startswith("OK")
    main(["validate", str(resources / "valid_single" / "reg.json")])
    assert capsys.readouterr().out.startswith("OK")
    with pytest.raises(SystemExit):
        main(["validate", str(resources / "invalid" / "missing_axis.json")])
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_validate_unknown_format(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "hist.txt"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["validate", str(bad)])
    assert "Unknown file format '.txt'" in capsys.readouterr().out


def test_cli_validate_zip(
    valid: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hists = json.loads(
        valid.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        for name, hist in hists.items():
            uhi.io.zip.write(zip_file, name, hist)

    main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("OK")


def test_cli_validate_zip_invalid(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        for name, hist in hists.items():
            uhi.io.zip.write(zip_file, name, hist)
        # A bare JSON entry without the required keys
        zip_file.writestr("broken.json", json.dumps({"uhi_schema": 1, "axes": []}))

    with pytest.raises(SystemExit):
        main(["validate", str(tmp_file)])
    out = capsys.readouterr().out
    assert out.startswith("ERROR")
    assert "storage" in out


def test_cli_validate_hdf5(
    valid: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    h5py = pytest.importorskip("h5py")
    uhi_io_hdf5 = pytest.importorskip("uhi.io.hdf5")

    hists = json.loads(
        valid.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        # Nest one level to check that groups are discovered recursively
        grp = h5_file.create_group("nested")
        for name, hist in hists.items():
            uhi_io_hdf5.write(grp.create_group(name), hist)

    main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("OK")


def test_cli_validate_hdf5_invalid(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    h5py = pytest.importorskip("h5py")
    uhi_io_hdf5 = pytest.importorskip("uhi.io.hdf5")

    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        for name, hist in hists.items():
            grp = h5_file.create_group(name)
            uhi_io_hdf5.write(grp, hist)
            grp["storage"].attrs["type"] = "not_a_storage"

    with pytest.raises(SystemExit):
        main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("ERROR")


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("data.json", ("data.json", None)),
        ("data.root:sub/dir", ("data.root", "sub/dir")),
        ("some/dir/data.h5:grp", ("some/dir/data.h5", "grp")),
        ("C:\\dir\\data.ROOT:grp", ("C:\\dir\\data.ROOT", "grp")),
        ("C:\\dir\\data.root", ("C:\\dir\\data.root", None)),
    ],
)
def test_split_spec(spec: str, expected: tuple[str, str | None]) -> None:
    assert uhi.io._files.split_spec(spec) == expected


def test_cli_validate_json_path(
    resources: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reg = resources / "valid" / "reg.json"
    single = uhi.schema.load(reg, path="one")
    assert single["uhi_schema"] == 1

    main(["validate", f"{reg}:one"])
    assert capsys.readouterr().out.startswith("OK")

    with pytest.raises(SystemExit):
        main(["validate", f"{reg}:missing"])
    assert "'missing' not found" in capsys.readouterr().out

    with pytest.raises(SystemExit):
        main(["validate", f"{resources / 'valid_single' / 'reg.json'}:one"])
    assert "'one' not found" in capsys.readouterr().out


def test_cli_validate_zip_path(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )
    tmp_file = tmp_path / "test.zip"
    with zipfile.ZipFile(tmp_file, "w") as zip_file:
        for name, hist in hists.items():
            uhi.io.zip.write(zip_file, f"good/{name}", hist)
            broken: Any = {
                **hist,
                "storage": {**hist["storage"], "type": "not_a_storage"},
            }
            uhi.io.zip.write(zip_file, f"bad/{name}", broken)

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
    assert "'missing' not found" in capsys.readouterr().out


def test_cli_validate_hdf5_path(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    h5py = pytest.importorskip("h5py")
    uhi_io_hdf5 = pytest.importorskip("uhi.io.hdf5")

    hists = json.loads(
        (resources / "valid" / "reg.json").read_text(encoding="utf-8"),
        object_hook=uhi.io.json.object_hook,
    )
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        good = h5_file.create_group("good")
        for name, hist in hists.items():
            uhi_io_hdf5.write(good.create_group(name), hist)
        bad = h5_file.create_group("bad")
        for name, hist in hists.items():
            grp = bad.create_group(name)
            uhi_io_hdf5.write(grp, hist)
            grp["storage"].attrs["type"] = "not_a_storage"

    assert set(uhi.schema.load(tmp_file, path="good")) == set(hists)
    assert set(uhi.schema.load(tmp_file, path="/good/")) == set(hists)
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


def test_cli_validate_json_keeps_raw_types(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loading for validation must not coerce JSON values into arrays."""
    bad = {
        "one": {
            "uhi_schema": 1,
            "axes": [{"type": "boolean"}],
            "storage": {"type": "double", "values": [True, 1]},
        }
    }
    tmp_file = tmp_path / "bad.json"
    tmp_file.write_text(json.dumps(bad), encoding="utf-8")

    with pytest.raises(fastjsonschema.exceptions.JsonSchemaException):
        uhi.schema.validate(uhi.schema.load(tmp_file))

    with pytest.raises(SystemExit):
        main(["validate", str(tmp_file)])
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_validate_no_fastjsonschema(
    resources: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "fastjsonschema", None)
    with pytest.raises(SystemExit, match=re.escape("uhi[schema]")):
        main(["validate", str(resources / "valid" / "reg.json")])


def test_cli_validate_empty_name(
    resources: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["validate", f"{resources / 'valid' / 'reg.json'}:"])
    assert "Empty name" in capsys.readouterr().out


def test_split_spec_empty_name() -> None:
    with pytest.raises(ValueError, match="Empty name"):
        uhi.io._files.split_spec("out.zip:")


def test_file_format_no_extension() -> None:
    with pytest.raises(ValueError, match="No file extension"):
        uhi.io._files.file_format(Path("out"))


def test_cli_validate_hdf5_dataset(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    h5py = pytest.importorskip("h5py")
    uhi_io_hdf5 = pytest.importorskip("uhi.io.hdf5")

    hists = uhi.io._files.load(resources / "valid" / "reg.json")
    tmp_file = tmp_path / "test.h5"
    with h5py.File(tmp_file, "w") as h5_file:
        uhi_io_hdf5.write(h5_file.create_group("one"), hists["one"])

    with pytest.raises(ValueError, match="not a histogram or group"):
        uhi.io._files.load(tmp_file, path="one/storage/values")
    with pytest.raises(KeyError, match="'missing' not found in"):
        uhi.io._files.load(tmp_file, path="missing")

    with pytest.raises(SystemExit):
        main(["validate", f"{tmp_file}:one/storage/values"])
    assert "not a histogram or group" in capsys.readouterr().out
