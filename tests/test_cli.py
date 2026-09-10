from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

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
    assert uhi.schema._split_spec(spec) == expected


def test_cli_validate_path_unsupported(
    resources: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["validate", f"{resources / 'valid' / 'reg.json'}:main"])
    assert "only supported for HDF5 and ROOT" in capsys.readouterr().out


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
